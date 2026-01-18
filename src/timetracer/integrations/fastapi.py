"""
FastAPI middleware for Timetracer.

This is the main integration point for FastAPI applications.
It handles request/response capture and session lifecycle.
"""

from __future__ import annotations

import json
import sys
import time
from typing import TYPE_CHECKING, Any

from timetracer.cassette import read_cassette, write_cassette
from timetracer.config import TraceConfig
from timetracer.context import reset_session, set_session
from timetracer.policies import redact_body, redact_headers, should_store_body
from timetracer.session import ReplaySession, TraceSession
from timetracer.types import BodySnapshot, RequestSnapshot, ResponseSnapshot
from timetracer.utils.hashing import hash_body

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class TimeTracerMiddleware:
    """
    ASGI middleware for Timetracer integration.

    Handles:
    - Session lifecycle (create, attach, finalize)
    - Request/response capture
    - Cassette writing (record mode)
    - Cassette loading (replay mode)
    - Terminal summary output

    Usage:
        from fastapi import FastAPI
        from timetracer.integrations.fastapi import TimeTracerMiddleware
        from timetracer.config import TraceConfig

        app = FastAPI()
        config = TraceConfig(mode="record", cassette_dir="./cassettes")
        app.add_middleware(TimeTracerMiddleware, config=config)
    """

    def __init__(
        self,
        app: ASGIApp,
        config: TraceConfig | None = None,
    ) -> None:
        """
        Initialize middleware.

        Args:
            app: The ASGI application.
            config: Timetracer configuration. If None, loads from environment.
        """
        self.app = app
        self.config = config or TraceConfig.from_env()

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request."""
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if timetrace is enabled
        if not self.config.is_enabled:
            await self.app(scope, receive, send)
            return

        # Get request path
        path = scope.get("path", "/")

        # Check if path should be traced
        if not self.config.should_trace(path):
            await self.app(scope, receive, send)
            return

        # Check sampling (only for record mode)
        if self.config.is_record_mode and not self.config.should_sample():
            await self.app(scope, receive, send)
            return

        # Route to appropriate handler
        if self.config.is_record_mode:
            await self._handle_record(scope, receive, send)
        elif self.config.is_replay_mode:
            await self._handle_replay(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    async def _handle_record(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle request in record mode."""
        # Create session
        session = TraceSession(config=self.config)
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Capture request
            request_snapshot = await self._capture_request(scope, receive)
            session.set_request(request_snapshot)

            # Create a new receive that returns already-read body
            body_bytes = b""
            if request_snapshot.body and request_snapshot.body.data:
                if request_snapshot.body.encoding == "json":
                    body_bytes = json.dumps(request_snapshot.body.data).encode()
                elif isinstance(request_snapshot.body.data, str):
                    body_bytes = request_snapshot.body.data.encode()
                elif isinstance(request_snapshot.body.data, bytes):
                    body_bytes = request_snapshot.body.data

            # Track response
            response_started = False
            response_status = 0
            response_headers: dict[str, str] = {}
            response_body_parts: list[bytes] = []

            async def send_wrapper(message: Message) -> None:
                nonlocal response_started, response_status, response_headers, response_body_parts

                if message["type"] == "http.response.start":
                    response_started = True
                    response_status = message.get("status", 0)
                    headers = message.get("headers", [])
                    response_headers = {
                        k.decode() if isinstance(k, bytes) else k:
                        v.decode() if isinstance(v, bytes) else v
                        for k, v in headers
                    }

                elif message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        response_body_parts.append(body)

                await send(message)

            # Create receive wrapper if we consumed the body
            body_consumed = False

            async def receive_wrapper() -> Message:
                nonlocal body_consumed
                if not body_consumed and body_bytes:
                    body_consumed = True
                    return {
                        "type": "http.request",
                        "body": body_bytes,
                        "more_body": False,
                    }
                return await receive()

            # Call the app
            is_error = False
            try:
                await self.app(scope, receive_wrapper, send_wrapper)
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

    async def _handle_replay(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle request in replay mode."""
        # Load cassette
        cassette_path = self.config.cassette_path
        if not cassette_path:
            # Try to find matching cassette by path
            # For now, require explicit cassette_path
            print("timetracer [WARN] replay mode requires TIMETRACER_CASSETTE", file=sys.stderr)
            await self.app(scope, receive, send)
            return

        cassette = read_cassette(cassette_path)

        # Create replay session
        session = ReplaySession(
            cassette=cassette,
            cassette_path=cassette_path,
            strict=self.config.strict_replay,
            config=self.config,  # Pass config for hybrid replay
        )
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Run the app (plugins will intercept dependency calls)
            await self.app(scope, receive, send)

            duration_ms = (time.perf_counter() - start_time) * 1000
            self._print_replay_summary(session, duration_ms)

        finally:
            reset_session(token)

    async def _capture_request(
        self,
        scope: Scope,
        receive: Receive,
    ) -> RequestSnapshot:
        """Capture incoming request data."""
        method = scope.get("method", "GET")
        path = scope.get("path", "/")

        # Get route template from scope (set by Starlette/FastAPI)
        route_template = None
        if "route" in scope:
            route = scope["route"]
            if hasattr(route, "path"):
                route_template = route.path

        # Headers
        raw_headers = scope.get("headers", [])
        headers = {
            k.decode() if isinstance(k, bytes) else k:
            v.decode() if isinstance(v, bytes) else v
            for k, v in raw_headers
        }

        # Redact sensitive headers
        headers = redact_headers(headers)

        # Query params
        query_string = scope.get("query_string", b"")
        query = self._parse_query_string(query_string)

        # Client info
        client = scope.get("client")
        client_ip = client[0] if client else None
        user_agent = headers.get("user-agent")

        # Body
        body_snapshot = await self._capture_request_body(receive)

        return RequestSnapshot(
            method=method,
            path=path,
            route_template=route_template,
            headers=headers,
            query=query,
            body=body_snapshot,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    async def _capture_request_body(
        self,
        receive: Receive,
    ) -> BodySnapshot | None:
        """Capture request body data."""
        # Always read the body (we need it for the app)
        body_parts: list[bytes] = []

        while True:
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    body_parts.append(body)
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        full_body = b"".join(body_parts)

        if not full_body:
            return None

        # Check size
        size_bytes = len(full_body)
        max_bytes = self.config.max_body_kb * 1024
        truncated = size_bytes > max_bytes

        if truncated:
            full_body = full_body[:max_bytes]

        # Try to parse as JSON
        encoding = "bytes"
        data: Any = None

        try:
            data = json.loads(full_body.decode("utf-8"))
            encoding = "json"
            # Redact sensitive data
            data = redact_body(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Store as base64 or hash only depending on policy
            encoding = "bytes"
            data = None

        return BodySnapshot(
            captured=True,
            encoding=encoding,
            data=data,
            truncated=truncated,
            size_bytes=size_bytes,
            hash=hash_body(full_body),
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

    def _parse_query_string(self, query_string: bytes) -> dict[str, str]:
        """Parse query string into dict."""
        if not query_string:
            return {}

        try:
            from urllib.parse import parse_qs
            qs = query_string.decode("utf-8")
            parsed = parse_qs(qs)
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


def auto_setup(
    app: Any,
    config: TraceConfig | None = None,
    plugins: list[str] | None = None,
) -> Any:
    """
    One-line Timetracer setup for FastAPI.

    Adds middleware and enables plugins automatically.

    Args:
        app: FastAPI application instance.
        config: Optional TraceConfig. If None, loads from environment.
        plugins: List of plugins to enable. Default: ["httpx"].
                 Options: "httpx", "requests", "sqlalchemy", "redis"

    Returns:
        The app instance (for chaining).

    Usage:
        from fastapi import FastAPI
        from timetracer.integrations.fastapi import auto_setup

        app = auto_setup(FastAPI())

        # Or with options:
        app = FastAPI()
        auto_setup(app, plugins=["httpx", "redis"])
    """
    from timetracer.plugins import enable_httpx

    cfg = config or TraceConfig.from_env()

    # Add middleware
    app.add_middleware(TimeTracerMiddleware, config=cfg)

    # Enable plugins
    enabled_plugins = plugins or ["httpx"]

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
        elif plugin == "aiohttp":
            from timetracer.plugins import enable_aiohttp
            enable_aiohttp()

    return app


# Backwards compatibility aliases
TimeTraceMiddleware = TimeTracerMiddleware  # Old name (deprecated)
timetracerMiddleware = TimeTracerMiddleware

