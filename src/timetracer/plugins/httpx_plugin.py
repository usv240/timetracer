"""
httpx plugin for Timetracer.

Captures and replays httpx HTTP client calls.
This is the primary plugin for mocking external API dependencies.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import parse_qs, urlparse

from timetracer.constants import EventType
from timetracer.context import get_current_session, has_active_session
from timetracer.policies import redact_headers_allowlist
from timetracer.types import (
    BodySnapshot,
    DependencyEvent,
    EventResult,
    EventSignature,
)
from timetracer.utils.hashing import hash_body

if TYPE_CHECKING:
    import httpx

# Store original methods for restoration
_original_async_send: Callable | None = None
_original_sync_send: Callable | None = None
_enabled = False


def enable_httpx() -> None:
    """
    Enable httpx interception for recording and replay.

    This patches httpx.AsyncClient.send and httpx.Client.send.
    Call disable_httpx() to restore original behavior.
    """
    global _original_async_send, _original_sync_send, _enabled

    if _enabled:
        return

    try:
        import httpx
    except ImportError:
        raise ImportError(
            "httpx is required for the httpx plugin. "
            "Install it with: pip install timetrace[httpx]"
        )

    # Patch AsyncClient
    _original_async_send = httpx.AsyncClient.send
    httpx.AsyncClient.send = _patched_async_send

    # Patch sync Client
    _original_sync_send = httpx.Client.send
    httpx.Client.send = _patched_sync_send

    _enabled = True


def disable_httpx() -> None:
    """
    Disable httpx interception and restore original behavior.
    """
    global _original_async_send, _original_sync_send, _enabled

    if not _enabled:
        return

    try:
        import httpx
    except ImportError:
        return

    # Restore originals
    if _original_async_send is not None:
        httpx.AsyncClient.send = _original_async_send
    if _original_sync_send is not None:
        httpx.Client.send = _original_sync_send

    _original_async_send = None
    _original_sync_send = None
    _enabled = False


async def _patched_async_send(
    self: "httpx.AsyncClient",
    request: "httpx.Request",
    **kwargs: Any,
) -> "httpx.Response":
    """Patched async send method."""
    # If no session, call original
    if not has_active_session():
        return await _original_async_send(self, request, **kwargs)  # type: ignore

    session = get_current_session()

    # Handle based on session mode
    if session.is_recording:
        return await _record_async_request(self, request, kwargs)
    elif session.is_replaying:
        # Check for hybrid replay - if plugin should stay live, make real call
        from timetracer.session import ReplaySession
        if isinstance(session, ReplaySession) and not session.should_mock_plugin("http"):
            return await _original_async_send(self, request, **kwargs)  # type: ignore
        return await _replay_async_request(request)
    else:
        return await _original_async_send(self, request, **kwargs)  # type: ignore


def _patched_sync_send(
    self: "httpx.Client",
    request: "httpx.Request",
    **kwargs: Any,
) -> "httpx.Response":
    """Patched sync send method."""
    # If no session, call original
    if not has_active_session():
        return _original_sync_send(self, request, **kwargs)  # type: ignore

    session = get_current_session()

    # Handle based on session mode
    if session.is_recording:
        return _record_sync_request(self, request, kwargs)
    elif session.is_replaying:
        # Check for hybrid replay - if plugin should stay live, make real call
        from timetracer.session import ReplaySession
        if isinstance(session, ReplaySession) and not session.should_mock_plugin("http"):
            return _original_sync_send(self, request, **kwargs)  # type: ignore
        return _replay_sync_request(request)
    else:
        return _original_sync_send(self, request, **kwargs)  # type: ignore


async def _record_async_request(
    client: "httpx.AsyncClient",
    request: "httpx.Request",
    kwargs: dict[str, Any],
) -> "httpx.Response":
    """Record an async httpx request."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return await _original_async_send(client, request, **kwargs)  # type: ignore

    start_offset = session.elapsed_ms
    start_time = time.perf_counter()

    # Make the actual request
    error_info = None
    response = None
    try:
        response = await _original_async_send(client, request, **kwargs)  # type: ignore
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build event
        event = _build_event(
            request=request,
            response=response,
            start_offset_ms=start_offset,
            duration_ms=duration_ms,
            error_info=error_info,
        )

        session.add_event(event)

    return response


def _record_sync_request(
    client: "httpx.Client",
    request: "httpx.Request",
    kwargs: dict[str, Any],
) -> "httpx.Response":
    """Record a sync httpx request."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return _original_sync_send(client, request, **kwargs)  # type: ignore

    start_offset = session.elapsed_ms
    start_time = time.perf_counter()

    # Make the actual request
    error_info = None
    response = None
    try:
        response = _original_sync_send(client, request, **kwargs)  # type: ignore
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build event
        event = _build_event(
            request=request,
            response=response,
            start_offset_ms=start_offset,
            duration_ms=duration_ms,
            error_info=error_info,
        )

        session.add_event(event)

    return response


async def _replay_async_request(
    request: "httpx.Request",
) -> "httpx.Response":
    """Replay an async httpx request from cassette."""
    from timetracer.session import ReplaySession

    session = get_current_session()
    if not isinstance(session, ReplaySession):
        raise RuntimeError("Expected ReplaySession for replay")

    # Build signature for matching
    actual_signature = _make_signature_dict(request)

    # Get expected event
    event = session.get_next_event(EventType.HTTP_CLIENT, actual_signature)

    # Build synthetic response
    return _build_synthetic_response(request, event)


def _replay_sync_request(
    request: "httpx.Request",
) -> "httpx.Response":
    """Replay a sync httpx request from cassette."""
    from timetracer.session import ReplaySession

    session = get_current_session()
    if not isinstance(session, ReplaySession):
        raise RuntimeError("Expected ReplaySession for replay")

    # Build signature for matching
    actual_signature = _make_signature_dict(request)

    # Get expected event
    event = session.get_next_event(EventType.HTTP_CLIENT, actual_signature)

    # Build synthetic response
    return _build_synthetic_response(request, event)


def _build_event(
    request: "httpx.Request",
    response: "httpx.Response | None",
    start_offset_ms: float,
    duration_ms: float,
    error_info: tuple[str, str] | None,
) -> DependencyEvent:
    """Build a DependencyEvent from httpx request/response."""
    # Build signature
    signature = _make_signature(request)

    # Build result
    result = _make_result(response, error_info)

    return DependencyEvent(
        eid=0,  # Will be set by session
        event_type=EventType.HTTP_CLIENT,
        start_offset_ms=start_offset_ms,
        duration_ms=duration_ms,
        signature=signature,
        result=result,
    )


def _make_signature(request: "httpx.Request") -> EventSignature:
    """Create EventSignature from httpx request."""
    # Normalize URL (scheme + host + path)
    url = str(request.url)
    parsed = urlparse(url)
    normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # Parse query params
    query = dict(parse_qs(parsed.query))
    # Flatten to single values
    query = {k: v[0] if len(v) == 1 else v for k, v in query.items()}

    # Hash request body
    body_hash = None
    if request.content:
        body_hash = hash_body(request.content)

    # Hash relevant headers
    headers_dict = dict(request.headers)
    allowed_headers = redact_headers_allowlist(headers_dict)
    headers_hash = hash_body(str(sorted(allowed_headers.items()))) if allowed_headers else None

    return EventSignature(
        lib="httpx",
        method=request.method,
        url=normalized_url,
        query=query,
        headers_hash=headers_hash,
        body_hash=body_hash,
    )


def _make_signature_dict(request: "httpx.Request") -> dict[str, Any]:
    """Create signature dict for matching."""
    sig = _make_signature(request)
    return {
        "lib": sig.lib,
        "method": sig.method,
        "url": sig.url,
        "query": sig.query,
        "body_hash": sig.body_hash,
    }


def _make_result(
    response: "httpx.Response | None",
    error_info: tuple[str, str] | None,
) -> EventResult:
    """Create EventResult from httpx response."""
    if error_info:
        return EventResult(
            error_type=error_info[0],
            error=error_info[1],
        )

    if response is None:
        return EventResult()

    # Capture response headers (allow-list)
    headers_dict = dict(response.headers)
    headers = redact_headers_allowlist(headers_dict)

    # Capture response body
    body_snapshot = None
    try:
        content = response.content
        if content:
            body_snapshot = BodySnapshot(
                captured=True,
                encoding="bytes",
                data=None,  # Don't store full body by default
                hash=hash_body(content),
                size_bytes=len(content),
            )

            # Try to parse as JSON for storage
            try:
                import json
                data = json.loads(content.decode("utf-8"))
                body_snapshot.encoding = "json"
                body_snapshot.data = data
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    except Exception:
        pass

    return EventResult(
        status=response.status_code,
        headers=headers,
        body=body_snapshot,
    )


def _build_synthetic_response(
    request: "httpx.Request",
    event: DependencyEvent,
) -> "httpx.Response":
    """Build a synthetic httpx.Response from recorded event."""
    import httpx

    result = event.result

    # Handle error case
    if result.error:
        # Raise the recorded error
        raise httpx.HTTPError(f"Recorded error: {result.error}")

    # Build response content
    content = b""
    if result.body and result.body.captured and result.body.data is not None:
        import json
        if result.body.encoding == "json":
            content = json.dumps(result.body.data).encode("utf-8")
        elif isinstance(result.body.data, str):
            content = result.body.data.encode("utf-8")
        elif isinstance(result.body.data, bytes):
            content = result.body.data

    # Build headers
    headers = result.headers.copy() if result.headers else {}
    if "content-length" not in {k.lower() for k in headers}:
        headers["content-length"] = str(len(content))

    # Create response
    return httpx.Response(
        status_code=result.status or 200,
        headers=headers,
        content=content,
        request=request,
    )
