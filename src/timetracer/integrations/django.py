"""
Django integration for Timetracer.

Supports Django 3.2 LTS and Django 4.0+.
Works with both sync and async views.
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
    from django.http import HttpRequest, HttpResponse


def _get_django_settings_config() -> dict[str, Any]:
    """Load Timetracer config from Django settings if available."""
    try:
        from django.conf import settings
        return getattr(settings, "TIMETRACER", {})
    except Exception:
        return {}


class TimeTracerMiddleware:
    """
    Django middleware for Timetracer integration.

    Supports both sync and async views (Django 4.1+).

    Usage with settings.py:
        MIDDLEWARE = [
            'timetracer.integrations.django.TimeTracerMiddleware',
            ...
        ]

        # Optional: configure via settings
        TIMETRACER = {
            'MODE': 'record',
            'CASSETTE_DIR': './cassettes',
        }

    Or configure via environment variables:
        TIMETRACER_MODE=record
        TIMETRACER_DIR=./cassettes
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Callable) -> None:
        """
        Initialize middleware.

        Args:
            get_response: The next middleware or view in the chain.
        """
        self.get_response = get_response
        self.config = self._load_config()

        # Check if get_response is async (Django 4.1+)
        import asyncio
        if asyncio.iscoroutinefunction(get_response):
            self._is_async = True
        else:
            self._is_async = False

    def _load_config(self) -> TraceConfig:
        """Load config from Django settings or environment."""
        django_settings = _get_django_settings_config()

        if django_settings:
            # Build config from Django settings
            return TraceConfig(
                mode=django_settings.get("MODE", "off"),
                cassette_dir=django_settings.get("CASSETTE_DIR", "./cassettes"),
                cassette_path=django_settings.get("CASSETTE_PATH"),
                sample_rate=django_settings.get("SAMPLE_RATE", 1.0),
                errors_only=django_settings.get("ERRORS_ONLY", False),
                exclude_paths=django_settings.get("EXCLUDE_PATHS", []),
                max_body_kb=django_settings.get("MAX_BODY_KB", 64),
                store_request_body=django_settings.get("STORE_REQUEST_BODY", "on_error"),
                store_response_body=django_settings.get("STORE_RESPONSE_BODY", "on_error"),
                mock_plugins=django_settings.get("MOCK_PLUGINS"),
                live_plugins=django_settings.get("LIVE_PLUGINS"),
            )
        else:
            # Fall back to environment variables
            return TraceConfig.from_env()

    def __call__(self, request: "HttpRequest") -> "HttpResponse":
        """Handle sync request."""
        if self._is_async:
            # Should not happen, but handle gracefully
            import asyncio
            return asyncio.get_event_loop().run_until_complete(
                self._async_call(request)
            )
        return self._sync_call(request)

    async def __acall__(self, request: "HttpRequest") -> "HttpResponse":
        """Handle async request (Django 4.1+)."""
        return await self._async_call(request)

    def _sync_call(self, request: "HttpRequest") -> "HttpResponse":
        """Sync request handler."""
        # Check if enabled
        if not self.config.is_enabled:
            return self.get_response(request)

        # Check if path should be traced
        if not self.config.should_trace(request.path):
            return self.get_response(request)

        # Check sampling
        if self.config.is_record_mode and not self.config.should_sample():
            return self.get_response(request)

        # Route to handler
        if self.config.is_record_mode:
            return self._handle_record_sync(request)
        elif self.config.is_replay_mode:
            return self._handle_replay_sync(request)
        else:
            return self.get_response(request)

    async def _async_call(self, request: "HttpRequest") -> "HttpResponse":
        """Async request handler."""
        # Check if enabled
        if not self.config.is_enabled:
            return await self.get_response(request)

        # Check if path should be traced
        if not self.config.should_trace(request.path):
            return await self.get_response(request)

        # Check sampling
        if self.config.is_record_mode and not self.config.should_sample():
            return await self.get_response(request)

        # Route to handler
        if self.config.is_record_mode:
            return await self._handle_record_async(request)
        elif self.config.is_replay_mode:
            return await self._handle_replay_async(request)
        else:
            return await self.get_response(request)

    def _handle_record_sync(self, request: "HttpRequest") -> "HttpResponse":
        """Handle sync request in record mode."""
        session = TraceSession(config=self.config)
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Capture request
            request_snapshot = self._capture_request(request)
            session.set_request(request_snapshot)

            # Call the view
            is_error = False
            try:
                response = self.get_response(request)
            except Exception as e:
                is_error = True
                session.mark_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Capture response if we got one
                if "response" in locals():
                    is_error = is_error or response.status_code >= 400
                    response_snapshot = self._build_response_snapshot(
                        response=response,
                        duration_ms=duration_ms,
                        is_error=is_error,
                    )
                    session.set_response(response_snapshot)

                # Finalize and write cassette
                session.finalize()

                if not self.config.errors_only or is_error:
                    cassette_path = write_cassette(session, self.config)
                    self._print_record_summary(session, cassette_path)

            return response

        finally:
            reset_session(token)

    async def _handle_record_async(self, request: "HttpRequest") -> "HttpResponse":
        """Handle async request in record mode."""
        session = TraceSession(config=self.config)
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            # Capture request
            request_snapshot = self._capture_request(request)
            session.set_request(request_snapshot)

            # Call the view
            is_error = False
            try:
                response = await self.get_response(request)
            except Exception as e:
                is_error = True
                session.mark_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                if "response" in locals():
                    is_error = is_error or response.status_code >= 400
                    response_snapshot = self._build_response_snapshot(
                        response=response,
                        duration_ms=duration_ms,
                        is_error=is_error,
                    )
                    session.set_response(response_snapshot)

                session.finalize()

                if not self.config.errors_only or is_error:
                    cassette_path = write_cassette(session, self.config)
                    self._print_record_summary(session, cassette_path)

            return response

        finally:
            reset_session(token)

    def _handle_replay_sync(self, request: "HttpRequest") -> "HttpResponse":
        """Handle sync request in replay mode."""
        cassette_path = self.config.cassette_path
        if not cassette_path:
            print("timetracer [WARN] replay mode requires TIMETRACER_CASSETTE", file=sys.stderr)
            return self.get_response(request)

        cassette = read_cassette(cassette_path)

        session = ReplaySession(
            cassette=cassette,
            cassette_path=cassette_path,
            strict=self.config.strict_replay,
            config=self.config,
        )
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            response = self.get_response(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._print_replay_summary(session, duration_ms)
            return response

        finally:
            reset_session(token)

    async def _handle_replay_async(self, request: "HttpRequest") -> "HttpResponse":
        """Handle async request in replay mode."""
        cassette_path = self.config.cassette_path
        if not cassette_path:
            print("timetracer [WARN] replay mode requires TIMETRACER_CASSETTE", file=sys.stderr)
            return await self.get_response(request)

        cassette = read_cassette(cassette_path)

        session = ReplaySession(
            cassette=cassette,
            cassette_path=cassette_path,
            strict=self.config.strict_replay,
            config=self.config,
        )
        token = set_session(session)

        start_time = time.perf_counter()

        try:
            response = await self.get_response(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._print_replay_summary(session, duration_ms)
            return response

        finally:
            reset_session(token)

    def _capture_request(self, request: "HttpRequest") -> RequestSnapshot:
        """Capture Django HttpRequest."""
        method = request.method
        path = request.path

        # Get route pattern if available (Django 2.0+)
        route_template = None
        if hasattr(request, "resolver_match") and request.resolver_match:
            route_template = request.resolver_match.route

        # Headers
        headers = {}
        for key, value in request.META.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-").lower()
                headers[header_name] = value

        headers = redact_headers(headers)

        # Query params
        query = dict(request.GET)
        # Flatten single-value lists
        query = {k: v[0] if len(v) == 1 else v for k, v in query.items()}

        # Client info
        client_ip = self._get_client_ip(request)
        user_agent = headers.get("user-agent")

        # Body
        body_snapshot = self._capture_request_body(request)

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

    def _get_client_ip(self, request: "HttpRequest") -> str | None:
        """Get client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _capture_request_body(self, request: "HttpRequest") -> BodySnapshot | None:
        """Capture request body."""
        try:
            body = request.body
        except Exception:
            return None

        if not body:
            return None

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
        response: "HttpResponse",
        duration_ms: float,
        is_error: bool,
    ) -> ResponseSnapshot:
        """Build response snapshot from Django HttpResponse."""
        from timetracer.policies import should_store_body

        status = response.status_code

        # Headers
        headers = {}
        for key, value in response.items():
            headers[key.lower()] = value
        headers = redact_headers(headers)

        # Body
        should_store = should_store_body(
            self.config.store_response_body,
            is_error=is_error,
        )

        body_snapshot = None
        try:
            body = response.content
        except Exception:
            body = b""

        if should_store and body:
            size_bytes = len(body)
            max_bytes = self.config.max_body_kb * 1024
            truncated = size_bytes > max_bytes

            if truncated:
                body = body[:max_bytes]

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

    def _print_record_summary(self, session: TraceSession, cassette_path: str) -> None:
        """Print terminal summary for record mode."""
        req = session.request
        res = session.response

        method = req.method if req else "???"
        path = req.path if req else "???"
        status = res.status if res else 0
        duration_ms = res.duration_ms if res else 0

        event_counts = {}
        for event in session.events:
            et = event.event_type.value
            event_counts[et] = event_counts.get(et, 0) + 1

        deps_str = ", ".join(f"{k}:{v}" for k, v in event_counts.items()) or "none"
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

        unconsumed = len(session.get_unconsumed_events())
        match_status = "OK" if unconsumed == 0 else f"WARN ({unconsumed} unconsumed)"

        mocked_count = session.current_cursor

        print(
            f"timetracer replay {method} {path}  "
            f"mocked={mocked_count}  matched={match_status}  "
            f"runtime={duration_ms:.0f}ms  recorded={recorded_duration:.0f}ms",
            file=sys.stderr,
        )


def auto_setup(
    plugins: list[str] | None = None,
) -> None:
    """
    Enable Timetracer plugins for Django.

    Call this in your Django settings.py or apps.py:

        from timetracer.integrations.django import auto_setup
        auto_setup(plugins=["httpx", "requests"])

    Args:
        plugins: List of plugins to enable. Default: ["requests"]
    """
    enabled_plugins = plugins or ["requests"]

    for plugin in enabled_plugins:
        if plugin == "httpx":
            from timetracer.plugins import enable_httpx
            enable_httpx()
        elif plugin == "requests":
            from timetracer.plugins import enable_requests
            enable_requests()
        elif plugin == "aiohttp":
            from timetracer.plugins import enable_aiohttp
            enable_aiohttp()
        elif plugin == "sqlalchemy":
            from timetracer.plugins import enable_sqlalchemy
            enable_sqlalchemy()
        elif plugin == "redis":
            from timetracer.plugins import enable_redis
            enable_redis()


# Alias for consistency
DjangoMiddleware = TimeTracerMiddleware
