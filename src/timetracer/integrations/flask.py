"""
Flask integration for Timetracer.

This is the main integration point for Flask applications.
It handles request/response capture and session lifecycle.
"""

from __future__ import annotations

import json
import sys
import time
from typing import TYPE_CHECKING, Any, Callable

from timetracer.cassette import read_cassette, write_cassette
from timetracer.config import TraceConfig
from timetracer.context import reset_session, set_session
from timetracer.policies import redact_body, redact_headers
from timetracer.session import ReplaySession, TraceSession
from timetracer.types import BodySnapshot, RequestSnapshot, ResponseSnapshot
from timetracer.utils.hashing import hash_body

if TYPE_CHECKING:
    from flask import Flask


class TimeTracerMiddleware:
    """
    WSGI middleware for Timetracer integration with Flask.

    Handles:
    - Session lifecycle (create, attach, finalize)
    - Request/response capture
    - Cassette writing (record mode)
    - Cassette loading (replay mode)
    - Terminal summary output

    Usage:
        from flask import Flask
        from timetracer.integrations.flask import TimeTracerMiddleware
        from timetracer.config import TraceConfig

        app = Flask(__name__)
        config = TraceConfig(mode="record", cassette_dir="./cassettes")
        app.wsgi_app = TimeTracerMiddleware(app.wsgi_app, config=config)
    """

    def __init__(
        self,
        app: Any,  # WSGI app
        config: TraceConfig | None = None,
    ) -> None:
        """
        Initialize middleware.

        Args:
            app: The WSGI application.
            config: Timetracer configuration. If None, loads from environment.
        """
        self.app = app
        self.config = config or TraceConfig.from_env()

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Any:
        """Handle WSGI request."""
        # Check if timetrace is enabled
        if not self.config.is_enabled:
            return self.app(environ, start_response)

        # Get request path
        path = environ.get("PATH_INFO", "/")

        # Check if path should be traced
        if not self.config.should_trace(path):
            return self.app(environ, start_response)

        # Check sampling (only for record mode)
        if self.config.is_record_mode and not self.config.should_sample():
            return self.app(environ, start_response)

        # Route to appropriate handler
        if self.config.is_record_mode:
            return self._handle_record(environ, start_response)
        elif self.config.is_replay_mode:
            return self._handle_replay(environ, start_response)
        else:
            return self.app(environ, start_response)

    def _handle_record(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Any:
        """Handle request in record mode."""
        # Create session
        session = TraceSession(config=self.config)
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Capture request
            request_snapshot = self._capture_request(environ)
            session.set_request(request_snapshot)

            # Track response
            response_started = False
            response_status = 0
            response_headers: dict[str, str] = {}
            response_body_parts: list[bytes] = []

            def capturing_start_response(status: str, headers: list, exc_info=None):
                nonlocal response_started, response_status, response_headers
                response_started = True
                # Parse status code from "200 OK"
                response_status = int(status.split()[0])
                response_headers = {k: v for k, v in headers}
                return start_response(status, headers, exc_info)

            # Call the app
            is_error = False
            try:
                response = self.app(environ, capturing_start_response)
                # Collect response body
                for chunk in response:
                    response_body_parts.append(chunk)
                    yield chunk
                if hasattr(response, 'close'):
                    response.close()
            except Exception as e:
                is_error = True
                session.mark_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
            finally:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Capture response
                is_error = is_error or response_status >= 400
                response_body = b"".join(response_body_parts)

                response_snapshot = self._build_response_snapshot(
                    status=response_status,
                    headers=response_headers,
                    body=response_body,
                    duration_ms=duration_ms,
                    is_error=is_error,
                )
                session.set_response(response_snapshot)

                # Finalize and write cassette
                session.finalize()

                # Only write if errors_only is False, or if there was an error
                if not self.config.errors_only or is_error:
                    cassette_path = write_cassette(session, self.config)
                    self._print_record_summary(session, cassette_path)

        finally:
            reset_session(token)

    def _handle_replay(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Any:
        """Handle request in replay mode."""
        # Load cassette
        cassette_path = self.config.cassette_path
        if not cassette_path:
            print("timetracer [WARN] replay mode requires TIMETRACER_CASSETTE", file=sys.stderr)
            return self.app(environ, start_response)

        cassette = read_cassette(cassette_path)

        # Create replay session
        session = ReplaySession(
            cassette=cassette,
            cassette_path=cassette_path,
            strict=self.config.strict_replay,
            config=self.config,
        )
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Run the app (plugins will intercept dependency calls)
            response = self.app(environ, start_response)
            response_body = b"".join(response)
            if hasattr(response, 'close'):
                response.close()

            duration_ms = (time.perf_counter() - start_time) * 1000
            self._print_replay_summary(session, duration_ms)

            yield response_body

        finally:
            reset_session(token)

    def _capture_request(self, environ: dict[str, Any]) -> RequestSnapshot:
        """Capture incoming request data."""
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        # Headers (from environ)
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-").lower()
                headers[header_name] = value

        # Redact sensitive headers
        headers = redact_headers(headers)

        # Query params
        query_string = environ.get("QUERY_STRING", "")
        query = self._parse_query_string(query_string)

        # Client info
        client_ip = environ.get("REMOTE_ADDR")
        user_agent = headers.get("user-agent")

        # Body
        body_snapshot = self._capture_request_body(environ)

        return RequestSnapshot(
            method=method,
            path=path,
            route_template=None,  # Flask doesn't expose this easily
            headers=headers,
            query=query,
            body=body_snapshot,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    def _capture_request_body(self, environ: dict[str, Any]) -> BodySnapshot | None:
        """Capture request body data."""
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length == 0:
            return None

        # Read body
        wsgi_input = environ.get("wsgi.input")
        if not wsgi_input:
            return None

        body = wsgi_input.read(content_length)

        # Put it back for the app to read
        from io import BytesIO
        environ["wsgi.input"] = BytesIO(body)

        if not body:
            return None

        # Check size
        size_bytes = len(body)
        max_bytes = self.config.max_body_kb * 1024
        truncated = size_bytes > max_bytes

        if truncated:
            body = body[:max_bytes]

        # Try to parse as JSON
        encoding = "bytes"
        data: Any = None

        try:
            data = json.loads(body.decode("utf-8"))
            encoding = "json"
            data = redact_body(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            encoding = "bytes"
            data = None

        return BodySnapshot(
            captured=True,
            encoding=encoding,
            data=data,
            truncated=truncated,
            size_bytes=size_bytes,
            hash=hash_body(body),
        )

    def _build_response_snapshot(
        self,
        status: int,
        headers: dict[str, str],
        body: bytes,
        duration_ms: float,
        is_error: bool,
    ) -> ResponseSnapshot:
        """Build response snapshot with policy-based capture."""
        from timetracer.policies import should_store_body

        # Redact headers
        headers = redact_headers(headers)

        # Check if we should store body
        should_store = should_store_body(
            self.config.store_response_body,
            is_error=is_error,
        )

        body_snapshot = None
        if should_store and body:
            size_bytes = len(body)
            max_bytes = self.config.max_body_kb * 1024
            truncated = size_bytes > max_bytes

            if truncated:
                body = body[:max_bytes]

            # Try to parse as JSON
            encoding = "bytes"
            data: Any = None

            try:
                data = json.loads(body.decode("utf-8"))
                encoding = "json"
                data = redact_body(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                encoding = "bytes"
                data = None

            body_snapshot = BodySnapshot(
                captured=True,
                encoding=encoding,
                data=data,
                truncated=truncated,
                size_bytes=size_bytes,
                hash=hash_body(body),
            )
        elif body:
            # Just store hash
            body_snapshot = BodySnapshot(
                captured=False,
                hash=hash_body(body),
                size_bytes=len(body),
            )

        return ResponseSnapshot(
            status=status,
            headers=headers,
            body=body_snapshot,
            duration_ms=duration_ms,
        )

    def _parse_query_string(self, query_string: str) -> dict[str, str]:
        """Parse query string into dict."""
        if not query_string:
            return {}

        try:
            from urllib.parse import parse_qs
            parsed = parse_qs(query_string)
            # Flatten to single values (take first)
            return {k: v[0] if v else "" for k, v in parsed.items()}
        except Exception:
            return {}

    def _print_record_summary(self, session: TraceSession, cassette_path: str) -> None:
        """Print terminal summary for record mode."""
        req = session.request
        res = session.response

        method = req.method if req else "???"
        path = req.path if req else "???"
        status = res.status if res else 0
        duration_ms = res.duration_ms if res else 0

        # Event counts
        event_counts = {}
        for event in session.events:
            et = event.event_type.value
            event_counts[et] = event_counts.get(et, 0) + 1

        deps_str = ", ".join(f"{k}:{v}" for k, v in event_counts.items()) or "none"

        # Status icon
        icon = "[OK]" if status < 400 else "[WARN]"

        print(
            f"timetracer {icon} recorded {method} {path}  "
            f"id={session.short_id}  status={status}  "
            f"total={duration_ms:.0f}ms  deps={deps_str}",
            file=sys.stderr,
        )
        print(f"  cassette: {cassette_path}", file=sys.stderr)

    def _print_replay_summary(self, session: ReplaySession, duration_ms: float) -> None:
        """Print terminal summary for replay mode."""
        req = session.request
        method = req.method
        path = req.path

        recorded_duration = session.cassette.response.duration_ms

        # Check for unconsumed events
        unconsumed = len(session.get_unconsumed_events())
        match_status = "OK" if unconsumed == 0 else f"WARN ({unconsumed} unconsumed)"

        # Mocked counts
        mocked_count = session.current_cursor

        print(
            f"timetracer replay {method} {path}  "
            f"mocked={mocked_count}  matched={match_status}  "
            f"runtime={duration_ms:.0f}ms  recorded={recorded_duration:.0f}ms",
            file=sys.stderr,
        )


def init_app(app: "Flask", config: TraceConfig | None = None) -> None:
    """
    Initialize Timetracer for a Flask app.

    Alternative to wrapping wsgi_app directly.

    Args:
        app: Flask application instance.
        config: Timetracer configuration.

    Usage:
        from flask import Flask
        from timetracer.integrations.flask import init_app
        from timetracer.config import TraceConfig

        app = Flask(__name__)
        init_app(app, TraceConfig(mode="record"))
    """
    cfg = config or TraceConfig.from_env()
    app.wsgi_app = TimeTracerMiddleware(app.wsgi_app, config=cfg)


def auto_setup(
    app: "Flask",
    config: TraceConfig | None = None,
    plugins: list[str] | None = None,
) -> "Flask":
    """
    One-line Timetracer setup for Flask.

    Adds middleware and enables plugins automatically.

    Args:
        app: Flask application instance.
        config: Optional TraceConfig. If None, loads from environment.
        plugins: List of plugins to enable. Default: ["requests"].
                 Options: "httpx", "requests", "sqlalchemy", "redis"

    Returns:
        The app instance (for chaining).

    Usage:
        from flask import Flask
        from timetracer.integrations.flask import auto_setup

        app = auto_setup(Flask(__name__))

        # Or with options:
        app = Flask(__name__)
        auto_setup(app, plugins=["requests", "redis"])
    """
    cfg = config or TraceConfig.from_env()

    # Add middleware
    app.wsgi_app = TimeTracerMiddleware(app.wsgi_app, config=cfg)

    # Enable plugins
    enabled_plugins = plugins or ["requests"]

    for plugin in enabled_plugins:
        if plugin == "httpx":
            from timetracer.plugins import enable_httpx
            enable_httpx()
        elif plugin == "requests":
            from timetracer.plugins import enable_requests
            enable_requests()
        elif plugin == "sqlalchemy":
            from timetracer.plugins import enable_sqlalchemy
            enable_sqlalchemy()
        elif plugin == "redis":
            from timetracer.plugins import enable_redis
            enable_redis()

    return app


# Backwards compatibility aliases
TimeTraceMiddleware = TimeTracerMiddleware  # Old name (deprecated)
timetracerMiddleware = TimeTracerMiddleware
