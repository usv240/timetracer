"""
Redis plugin for Timetracer.

Captures and replays Redis commands.
This enables recording Redis interactions for deterministic replay.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

from timetracer.constants import EventType
from timetracer.context import get_current_session, has_active_session
from timetracer.types import (
    BodySnapshot,
    DependencyEvent,
    EventResult,
    EventSignature,
)
from timetracer.utils.hashing import hash_body

if TYPE_CHECKING:
    import redis

# Store original methods for restoration
_original_execute_command: Callable | None = None
_original_pipeline_execute: Callable | None = None
_enabled = False


def enable_redis() -> None:
    """
    Enable Redis interception for recording and replay.

    This patches redis.Redis.execute_command.
    Call disable_redis() to restore original behavior.
    """
    global _original_execute_command, _original_pipeline_execute, _enabled

    if _enabled:
        return

    try:
        import redis as redis_lib
    except ImportError:
        raise ImportError(
            "redis is required for the redis plugin. "
            "Install it with: pip install redis"
        )

    # Patch Redis.execute_command
    _original_execute_command = redis_lib.Redis.execute_command
    redis_lib.Redis.execute_command = _patched_execute_command

    # Patch Pipeline.execute (for pipeline commands)
    _original_pipeline_execute = redis_lib.client.Pipeline.execute
    redis_lib.client.Pipeline.execute = _patched_pipeline_execute

    _enabled = True


def disable_redis() -> None:
    """
    Disable Redis interception and restore original behavior.
    """
    global _original_execute_command, _original_pipeline_execute, _enabled

    if not _enabled:
        return

    try:
        import redis as redis_lib
    except ImportError:
        return

    # Restore originals
    if _original_execute_command is not None:
        redis_lib.Redis.execute_command = _original_execute_command

    if _original_pipeline_execute is not None:
        redis_lib.client.Pipeline.execute = _original_pipeline_execute

    _original_execute_command = None
    _original_pipeline_execute = None
    _enabled = False


def _patched_execute_command(
    self: "redis.Redis",
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched execute_command method."""
    # If no session, call original
    if not has_active_session():
        return _original_execute_command(self, *args, **kwargs)  # type: ignore

    session = get_current_session()

    # Handle based on session mode
    if session.is_recording:
        return _record_command(self, args, kwargs)
    elif session.is_replaying:
        # Check for hybrid replay - if plugin should stay live, make real call
        from timetracer.session import ReplaySession
        if isinstance(session, ReplaySession) and not session.should_mock_plugin("redis"):
            return _original_execute_command(self, *args, **kwargs)  # type: ignore
        return _replay_command(args, kwargs)
    else:
        return _original_execute_command(self, *args, **kwargs)  # type: ignore


def _patched_pipeline_execute(
    self: "redis.client.Pipeline",
    raise_on_error: bool = True,
) -> list:
    """Patched pipeline execute method."""
    # For now, just call original - pipeline tracking is complex
    # TODO: Add full pipeline support in v2.1
    return _original_pipeline_execute(self, raise_on_error)  # type: ignore


def _record_command(
    client: "redis.Redis",
    args: tuple,
    kwargs: dict[str, Any],
) -> Any:
    """Record a Redis command."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return _original_execute_command(client, *args, **kwargs)  # type: ignore

    start_offset = session.elapsed_ms
    start_time = time.perf_counter()

    # Make the actual call
    error_info = None
    result = None
    try:
        result = _original_execute_command(client, *args, **kwargs)  # type: ignore
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build event
        event = _build_event(
            args=args,
            kwargs=kwargs,
            result=result,
            start_offset_ms=start_offset,
            duration_ms=duration_ms,
            error_info=error_info,
        )

        session.add_event(event)

    return result


def _replay_command(
    args: tuple,
    kwargs: dict[str, Any],
) -> Any:
    """Replay a Redis command from cassette."""
    from timetracer.session import ReplaySession

    session = get_current_session()
    if not isinstance(session, ReplaySession):
        raise RuntimeError("Expected ReplaySession for replay")

    # Build signature for matching
    actual_signature = _make_signature_dict(args, kwargs)

    # Get expected event
    event = session.get_next_event(EventType.REDIS, actual_signature)

    # Return recorded result
    return _extract_result(event)


def _build_event(
    args: tuple,
    kwargs: dict[str, Any],
    result: Any,
    start_offset_ms: float,
    duration_ms: float,
    error_info: tuple[str, str] | None,
) -> DependencyEvent:
    """Build a DependencyEvent from Redis command."""
    # Build signature
    signature = _make_signature(args, kwargs)

    # Build result
    event_result = _make_result(result, error_info)

    return DependencyEvent(
        eid=0,  # Will be set by session
        event_type=EventType.REDIS,
        start_offset_ms=start_offset_ms,
        duration_ms=duration_ms,
        signature=signature,
        result=event_result,
    )


def _make_signature(args: tuple, kwargs: dict[str, Any]) -> EventSignature:
    """Create EventSignature from Redis command."""
    # First arg is command name
    command = str(args[0]).upper() if args else "UNKNOWN"

    # Key is typically second arg
    key = str(args[1]) if len(args) > 1 else ""

    # Hash remaining args
    args_hash = None
    if len(args) > 2:
        try:
            args_hash = hash_body(str(args[2:]))
        except Exception:
            pass

    return EventSignature(
        lib="redis",
        method=command,  # GET, SET, HGET, etc.
        url=key,  # Use url field for key
        query={},
        body_hash=args_hash,
    )


def _make_signature_dict(args: tuple, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Create signature dict for matching."""
    sig = _make_signature(args, kwargs)
    return {
        "lib": sig.lib,
        "method": sig.method,
        "url": sig.url,
        "body_hash": sig.body_hash,
    }


def _make_result(
    result: Any,
    error_info: tuple[str, str] | None,
) -> EventResult:
    """Create EventResult from Redis response."""
    if error_info:
        return EventResult(
            error_type=error_info[0],
            error=error_info[1],
        )

    # Store simple result types
    body_snapshot = None
    if result is not None:
        try:
            # Handle different result types
            if isinstance(result, bytes):
                data = result.decode("utf-8", errors="replace")
            elif isinstance(result, (list, dict)):
                data = result
            else:
                data = str(result)

            body_snapshot = BodySnapshot(
                captured=True,
                encoding="json" if isinstance(data, (list, dict)) else "text",
                data=data,
            )
        except Exception:
            pass

    return EventResult(
        status=1 if result is not None else 0,
        body=body_snapshot,
    )


def _extract_result(event: DependencyEvent) -> Any:
    """Extract result from recorded event."""
    result = event.result

    # Handle error case
    if result.error:
        import redis
        raise redis.RedisError(f"Recorded error: {result.error}")

    # Return captured data
    if result.body and result.body.captured and result.body.data is not None:
        return result.body.data

    return None
