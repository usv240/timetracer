"""
aiohttp plugin for Timetracer.

Captures and replays aiohttp HTTP client calls.
This plugin supports async HTTP client operations via aiohttp.ClientSession.
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
    import aiohttp

# Store original method for restoration
_original_request: Callable | None = None
_enabled = False


def enable_aiohttp() -> None:
    """
    Enable aiohttp interception for recording and replay.

    This patches aiohttp.ClientSession._request.
    Call disable_aiohttp() to restore original behavior.
    """
    global _original_request, _enabled

    if _enabled:
        return

    try:
        import aiohttp
    except ImportError:
        raise ImportError(
            "aiohttp is required for the aiohttp plugin. "
            "Install it with: pip install timetracer[aiohttp]"
        )

    # Patch ClientSession._request
    _original_request = aiohttp.ClientSession._request
    aiohttp.ClientSession._request = _patched_request

    _enabled = True


def disable_aiohttp() -> None:
    """
    Disable aiohttp interception and restore original behavior.
    """
    global _original_request, _enabled

    if not _enabled:
        return

    try:
        import aiohttp
    except ImportError:
        return

    # Restore original
    if _original_request is not None:
        aiohttp.ClientSession._request = _original_request

    _original_request = None
    _enabled = False


async def _patched_request(
    self: "aiohttp.ClientSession",
    method: str,
    str_or_url: Any,
    **kwargs: Any,
) -> "aiohttp.ClientResponse":
    """Patched _request method."""
    # If no session, call original
    if not has_active_session():
        return await _original_request(self, method, str_or_url, **kwargs)  # type: ignore

    session = get_current_session()

    # Handle based on session mode
    if session.is_recording:
        return await _record_request(self, method, str_or_url, kwargs)
    elif session.is_replaying:
        # Check for hybrid replay - if plugin should stay live, make real call
        from timetracer.session import ReplaySession
        if isinstance(session, ReplaySession) and not session.should_mock_plugin("http"):
            return await _original_request(self, method, str_or_url, **kwargs)  # type: ignore
        return await _replay_request(method, str_or_url, kwargs)
    else:
        return await _original_request(self, method, str_or_url, **kwargs)  # type: ignore


async def _record_request(
    client: "aiohttp.ClientSession",
    method: str,
    str_or_url: Any,
    kwargs: dict[str, Any],
) -> "aiohttp.ClientResponse":
    """Record an aiohttp request."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return await _original_request(client, method, str_or_url, **kwargs)  # type: ignore

    start_offset = session.elapsed_ms
    start_time = time.perf_counter()

    # Make the actual request
    error_info = None
    response = None
    response_body = None
    try:
        response = await _original_request(client, method, str_or_url, **kwargs)  # type: ignore
        # Read the response body for recording
        # We need to read it now because aiohttp responses can only be read once
        response_body = await response.read()
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build event
        event = _build_event(
            method=method,
            url=str(str_or_url),
            request_kwargs=kwargs,
            response=response,
            response_body=response_body,
            start_offset_ms=start_offset,
            duration_ms=duration_ms,
            error_info=error_info,
        )

        session.add_event(event)

    return response


async def _replay_request(
    method: str,
    str_or_url: Any,
    kwargs: dict[str, Any],
) -> "aiohttp.ClientResponse":
    """Replay an aiohttp request from cassette."""
    from timetracer.session import ReplaySession

    session = get_current_session()
    if not isinstance(session, ReplaySession):
        raise RuntimeError("Expected ReplaySession for replay")

    # Build signature for matching
    actual_signature = _make_signature_dict(method, str(str_or_url), kwargs)

    # Get expected event
    event = session.get_next_event(EventType.HTTP_CLIENT, actual_signature)

    # Build synthetic response
    return _build_synthetic_response(method, str_or_url, event)


def _build_event(
    method: str,
    url: str,
    request_kwargs: dict[str, Any],
    response: "aiohttp.ClientResponse | None",
    response_body: bytes | None,
    start_offset_ms: float,
    duration_ms: float,
    error_info: tuple[str, str] | None,
) -> DependencyEvent:
    """Build a DependencyEvent from aiohttp request/response."""
    # Build signature
    signature = _make_signature(method, url, request_kwargs)

    # Build result
    result = _make_result(response, response_body, error_info)

    return DependencyEvent(
        eid=0,  # Will be set by session
        event_type=EventType.HTTP_CLIENT,
        start_offset_ms=start_offset_ms,
        duration_ms=duration_ms,
        signature=signature,
        result=result,
    )


def _make_signature(
    method: str,
    url: str,
    kwargs: dict[str, Any],
) -> EventSignature:
    """Create EventSignature from aiohttp request."""
    # Normalize URL (scheme + host + path)
    parsed = urlparse(url)
    normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # Parse query params from URL
    query = dict(parse_qs(parsed.query))
    # Flatten to single values
    query = {k: v[0] if len(v) == 1 else v for k, v in query.items()}

    # Also check for params in kwargs
    if "params" in kwargs and kwargs["params"]:
        params = kwargs["params"]
        if isinstance(params, dict):
            query.update(params)

    # Hash request body
    body_hash = None
    if "data" in kwargs and kwargs["data"]:
        data = kwargs["data"]
        if isinstance(data, bytes):
            body_hash = hash_body(data)
        elif isinstance(data, str):
            body_hash = hash_body(data.encode("utf-8"))
        elif isinstance(data, dict):
            import json
            body_hash = hash_body(json.dumps(data, sort_keys=True).encode("utf-8"))
    elif "json" in kwargs and kwargs["json"]:
        import json
        body_hash = hash_body(json.dumps(kwargs["json"], sort_keys=True).encode("utf-8"))

    # Hash relevant headers
    headers_hash = None
    if "headers" in kwargs and kwargs["headers"]:
        headers_dict = dict(kwargs["headers"])
        allowed_headers = redact_headers_allowlist(headers_dict)
        headers_hash = hash_body(str(sorted(allowed_headers.items()))) if allowed_headers else None

    return EventSignature(
        lib="aiohttp",
        method=method.upper(),
        url=normalized_url,
        query=query,
        headers_hash=headers_hash,
        body_hash=body_hash,
    )


def _make_signature_dict(
    method: str,
    url: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
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
    response: "aiohttp.ClientResponse | None",
    response_body: bytes | None,
    error_info: tuple[str, str] | None,
) -> EventResult:
    """Create EventResult from aiohttp response."""
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
    if response_body:
        body_snapshot = BodySnapshot(
            captured=True,
            encoding="bytes",
            data=None,  # Don't store full body by default
            hash=hash_body(response_body),
            size_bytes=len(response_body),
        )

        # Try to parse as JSON for storage
        try:
            import json
            data = json.loads(response_body.decode("utf-8"))
            body_snapshot.encoding = "json"
            body_snapshot.data = data
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    return EventResult(
        status=response.status,
        headers=headers,
        body=body_snapshot,
    )


def _build_synthetic_response(
    method: str,
    url: Any,
    event: DependencyEvent,
) -> "aiohttp.ClientResponse":
    """Build a synthetic aiohttp.ClientResponse from recorded event."""
    import aiohttp
    from multidict import CIMultiDict
    from yarl import URL

    result = event.result

    # Handle error case
    if result.error:
        # Raise the recorded error
        raise aiohttp.ClientError(f"Recorded error: {result.error}")

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
    headers = CIMultiDict(result.headers) if result.headers else CIMultiDict()
    if "content-length" not in {k.lower() for k in headers}:
        headers["content-length"] = str(len(content))

    # Create a mock response
    # aiohttp's ClientResponse is complex, so we create a simpler wrapper
    response = _MockClientResponse(
        method=method,
        url=URL(str(url)),
        status=result.status or 200,
        headers=headers,
        content=content,
    )

    return response


class _MockClientResponse:
    """
    Mock aiohttp ClientResponse for replay.

    This provides the essential interface of aiohttp.ClientResponse
    without requiring an actual connection.
    """

    def __init__(
        self,
        method: str,
        url: Any,
        status: int,
        headers: Any,
        content: bytes,
    ):
        from multidict import CIMultiDict
        from yarl import URL

        self.method = method
        self.url = URL(str(url)) if not isinstance(url, URL) else url
        self.status = status
        self._headers = CIMultiDict(headers) if not isinstance(headers, CIMultiDict) else headers
        self._content = content
        self._body = content
        self.reason = "OK" if status < 400 else "Error"
        self.ok = 200 <= status < 300

    @property
    def headers(self):
        from multidict import CIMultiDictProxy
        return CIMultiDictProxy(self._headers)

    async def read(self) -> bytes:
        """Read response body."""
        return self._content

    async def text(self, encoding: str | None = None) -> str:
        """Read response body as text."""
        enc = encoding or "utf-8"
        return self._content.decode(enc)

    async def json(self, **kwargs) -> Any:
        """Read response body as JSON."""
        import json
        return json.loads(self._content.decode("utf-8"))

    def raise_for_status(self) -> None:
        """Raise exception if status is error."""
        if self.status >= 400:
            import aiohttp
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message=self.reason,
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def release(self):
        pass

    async def wait_for_close(self):
        pass
