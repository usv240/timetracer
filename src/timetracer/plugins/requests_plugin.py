"""
requests plugin for Timetracer.

Captures and replays requests library HTTP calls.
This provides compatibility for codebases using requests instead of httpx.
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
    import requests

# Store original method for restoration
_original_request: Callable | None = None
_enabled = False


def enable_requests() -> None:
    """
    Enable requests interception for recording and replay.

    This patches requests.Session.request.
    Call disable_requests() to restore original behavior.
    """
    global _original_request, _enabled

    if _enabled:
        return

    try:
        import requests
    except ImportError:
        raise ImportError(
            "requests is required for the requests plugin. "
            "Install it with: pip install requests"
        )

    # Patch Session.request (all requests go through this)
    _original_request = requests.Session.request
    requests.Session.request = _patched_request

    _enabled = True


def disable_requests() -> None:
    """
    Disable requests interception and restore original behavior.
    """
    global _original_request, _enabled

    if not _enabled:
        return

    try:
        import requests
    except ImportError:
        return

    # Restore original
    if _original_request is not None:
        requests.Session.request = _original_request

    _original_request = None
    _enabled = False


def _patched_request(
    self: "requests.Session",
    method: str,
    url: str,
    **kwargs: Any,
) -> "requests.Response":
    """Patched request method."""
    # If no session, call original
    if not has_active_session():
        return _original_request(self, method, url, **kwargs)  # type: ignore

    session = get_current_session()

    # Handle based on session mode
    if session.is_recording:
        return _record_request(self, method, url, kwargs)
    elif session.is_replaying:
        # Check for hybrid replay - if plugin should stay live, make real call
        from timetracer.session import ReplaySession
        if isinstance(session, ReplaySession) and not session.should_mock_plugin("http"):
            return _original_request(self, method, url, **kwargs)  # type: ignore
        return _replay_request(method, url, kwargs)
    else:
        return _original_request(self, method, url, **kwargs)  # type: ignore


def _record_request(
    client: "requests.Session",
    method: str,
    url: str,
    kwargs: dict[str, Any],
) -> "requests.Response":
    """Record a requests call."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return _original_request(client, method, url, **kwargs)  # type: ignore

    start_offset = session.elapsed_ms
    start_time = time.perf_counter()

    # Make the actual request
    error_info = None
    response = None
    try:
        response = _original_request(client, method, url, **kwargs)  # type: ignore
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build event
        event = _build_event(
            method=method,
            url=url,
            kwargs=kwargs,
            response=response,
            start_offset_ms=start_offset,
            duration_ms=duration_ms,
            error_info=error_info,
        )

        session.add_event(event)

    return response


def _replay_request(
    method: str,
    url: str,
    kwargs: dict[str, Any],
) -> "requests.Response":
    """Replay a requests call from cassette."""
    from timetracer.session import ReplaySession

    session = get_current_session()
    if not isinstance(session, ReplaySession):
        raise RuntimeError("Expected ReplaySession for replay")

    # Build signature for matching
    actual_signature = _make_signature_dict(method, url, kwargs)

    # Get expected event
    event = session.get_next_event(EventType.HTTP_CLIENT, actual_signature)

    # Build synthetic response
    return _build_synthetic_response(event)


def _build_event(
    method: str,
    url: str,
    kwargs: dict[str, Any],
    response: "requests.Response | None",
    start_offset_ms: float,
    duration_ms: float,
    error_info: tuple[str, str] | None,
) -> DependencyEvent:
    """Build a DependencyEvent from requests call."""
    # Build signature
    signature = _make_signature(method, url, kwargs)

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


def _make_signature(method: str, url: str, kwargs: dict[str, Any]) -> EventSignature:
    """Create EventSignature from requests call."""
    # Normalize URL
    parsed = urlparse(url)
    normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # Parse query params (from URL or kwargs)
    query = dict(parse_qs(parsed.query))
    if "params" in kwargs and kwargs["params"]:
        params = kwargs["params"]
        if isinstance(params, dict):
            query.update({k: [v] if not isinstance(v, list) else v for k, v in params.items()})
    # Flatten single-value lists
    query = {k: v[0] if len(v) == 1 else v for k, v in query.items()}

    # Hash request body
    body_hash = None
    if "data" in kwargs and kwargs["data"]:
        body_hash = hash_body(kwargs["data"])
    elif "json" in kwargs and kwargs["json"]:
        body_hash = hash_body(kwargs["json"])

    # Hash relevant headers
    headers_hash = None
    if "headers" in kwargs and kwargs["headers"]:
        allowed_headers = redact_headers_allowlist(kwargs["headers"])
        if allowed_headers:
            headers_hash = hash_body(str(sorted(allowed_headers.items())))

    return EventSignature(
        lib="requests",
        method=method.upper(),
        url=normalized_url,
        query=query,
        headers_hash=headers_hash,
        body_hash=body_hash,
    )


def _make_signature_dict(method: str, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Create signature dict for matching."""
    sig = _make_signature(method, url, kwargs)
    return {
        "lib": sig.lib,
        "method": sig.method,
        "url": sig.url,
        "query": sig.query,
        "body_hash": sig.body_hash,
    }


def _make_result(
    response: "requests.Response | None",
    error_info: tuple[str, str] | None,
) -> EventResult:
    """Create EventResult from requests response."""
    if error_info:
        return EventResult(
            error_type=error_info[0],
            error=error_info[1],
        )

    if response is None:
        return EventResult()

    # Capture response headers (allow-list)
    headers = dict(response.headers)
    filtered_headers = redact_headers_allowlist(headers)

    # Capture response body
    body_snapshot = None
    try:
        content = response.content
        if content:
            body_snapshot = BodySnapshot(
                captured=True,
                encoding="bytes",
                data=None,
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
        headers=filtered_headers,
        body=body_snapshot,
    )


def _build_synthetic_response(event: DependencyEvent) -> "requests.Response":
    """Build a synthetic requests.Response from recorded event."""
    import requests
    from requests.structures import CaseInsensitiveDict

    result = event.result

    # Handle error case
    if result.error:
        raise requests.RequestException(f"Recorded error: {result.error}")

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
    headers = CaseInsensitiveDict(result.headers or {})
    if "content-length" not in headers:
        headers["content-length"] = str(len(content))

    # Create response object
    response = requests.Response()
    response.status_code = result.status or 200
    response.headers = headers
    response._content = content
    response.encoding = "utf-8"

    return response
