"""
SQLAlchemy plugin for Timetracer.

Captures and replays SQLAlchemy database queries.
This enables recording database interactions for deterministic replay.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from timetracer.constants import EventType
from timetracer.context import get_current_session, has_active_session
from timetracer.types import (
    DependencyEvent,
    EventResult,
    EventSignature,
)
from timetracer.utils.hashing import hash_body

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine

# Store original state for restoration
_enabled = False
_listeners_attached = False


def enable_sqlalchemy(engine: "Engine | None" = None) -> None:
    """
    Enable SQLAlchemy interception for recording and replay.

    This attaches event listeners to capture query execution.
    Call disable_sqlalchemy() to restore original behavior.

    Args:
        engine: Optional specific engine. If None, uses global event.
    """
    global _enabled, _listeners_attached

    if _enabled:
        return

    try:
        from sqlalchemy import event as sa_event
        from sqlalchemy.engine import Engine
    except ImportError:
        raise ImportError(
            "sqlalchemy is required for the sqlalchemy plugin. "
            "Install it with: pip install sqlalchemy"
        )

    # Attach listeners
    if engine is not None:
        sa_event.listen(engine, "before_cursor_execute", _before_cursor_execute)
        sa_event.listen(engine, "after_cursor_execute", _after_cursor_execute)
    else:
        # Global listener for all engines
        sa_event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
        sa_event.listen(Engine, "after_cursor_execute", _after_cursor_execute)

    _listeners_attached = True
    _enabled = True


def disable_sqlalchemy(engine: "Engine | None" = None) -> None:
    """
    Disable SQLAlchemy interception and restore original behavior.
    """
    global _enabled, _listeners_attached

    if not _enabled:
        return

    try:
        from sqlalchemy import event as sa_event
        from sqlalchemy.engine import Engine
    except ImportError:
        return

    # Remove listeners
    if engine is not None:
        sa_event.remove(engine, "before_cursor_execute", _before_cursor_execute)
        sa_event.remove(engine, "after_cursor_execute", _after_cursor_execute)
    else:
        sa_event.remove(Engine, "before_cursor_execute", _before_cursor_execute)
        sa_event.remove(Engine, "after_cursor_execute", _after_cursor_execute)

    _listeners_attached = False
    _enabled = False


# Thread-local storage for timing
_query_timing = threading.local()


def _before_cursor_execute(
    conn: "Connection",
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """Event listener called before query execution."""
    if not has_active_session():
        return

    session = get_current_session()

    # Store timing info
    _query_timing.start_time = time.perf_counter()
    _query_timing.start_offset = session.elapsed_ms if hasattr(session, 'elapsed_ms') else 0
    _query_timing.statement = statement
    _query_timing.parameters = parameters


def _after_cursor_execute(
    conn: "Connection",
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """Event listener called after query execution."""
    if not has_active_session():
        return

    session = get_current_session()

    # Check if we have timing info
    if not hasattr(_query_timing, 'start_time'):
        return

    # Handle based on session mode
    if session.is_recording:
        _record_query(
            conn, cursor, statement, parameters, context, executemany
        )
    # Replay is handled differently for DB - we can't easily mock cursor results
    # For now, just record and skip replay mocking


def _record_query(
    conn: "Connection",
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """Record a database query."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return

    # Calculate duration
    duration_ms = (time.perf_counter() - _query_timing.start_time) * 1000
    start_offset = getattr(_query_timing, 'start_offset', 0)

    # Build event
    event = _build_event(
        statement=statement,
        parameters=parameters,
        cursor=cursor,
        start_offset_ms=start_offset,
        duration_ms=duration_ms,
        executemany=executemany,
    )

    session.add_event(event)


def _build_event(
    statement: str,
    parameters: Any,
    cursor: Any,
    start_offset_ms: float,
    duration_ms: float,
    executemany: bool,
) -> DependencyEvent:
    """Build a DependencyEvent from SQLAlchemy query."""
    # Build signature
    signature = _make_signature(statement, parameters)

    # Build result (basic - just rowcount)
    result = _make_result(cursor)

    return DependencyEvent(
        eid=0,  # Will be set by session
        event_type=EventType.DB_QUERY,
        start_offset_ms=start_offset_ms,
        duration_ms=duration_ms,
        signature=signature,
        result=result,
    )


def _make_signature(statement: str, parameters: Any) -> EventSignature:
    """Create EventSignature from SQLAlchemy query."""
    # Normalize statement (strip whitespace)
    normalized = " ".join(statement.split())

    # Extract operation type
    operation = normalized.split()[0].upper() if normalized else "UNKNOWN"

    # Hash parameters
    params_hash = None
    if parameters:
        try:
            params_hash = hash_body(str(parameters))
        except Exception:
            params_hash = None

    # Extract table name (basic parsing)
    table = _extract_table_name(normalized, operation)

    return EventSignature(
        lib="sqlalchemy",
        method=operation,  # SELECT, INSERT, UPDATE, DELETE
        url=table,  # Use url field for table name
        query={},
        body_hash=params_hash,
    )


def _extract_table_name(statement: str, operation: str) -> str:
    """Extract table name from SQL statement."""
    statement_upper = statement.upper()

    try:
        if operation == "SELECT":
            # SELECT ... FROM table_name
            from_idx = statement_upper.find(" FROM ")
            if from_idx != -1:
                after_from = statement[from_idx + 6:].strip()
                return after_from.split()[0].strip("();")

        elif operation == "INSERT":
            # INSERT INTO table_name
            into_idx = statement_upper.find(" INTO ")
            if into_idx != -1:
                after_into = statement[into_idx + 6:].strip()
                return after_into.split()[0].strip("();")

        elif operation == "UPDATE":
            # UPDATE table_name
            parts = statement.split()
            if len(parts) > 1:
                return parts[1].strip("();")

        elif operation == "DELETE":
            # DELETE FROM table_name
            from_idx = statement_upper.find(" FROM ")
            if from_idx != -1:
                after_from = statement[from_idx + 6:].strip()
                return after_from.split()[0].strip("();")
    except Exception:
        pass

    return "unknown"


def _make_result(cursor: Any) -> EventResult:
    """Create EventResult from cursor."""
    rowcount = -1
    try:
        rowcount = cursor.rowcount
    except Exception:
        pass

    return EventResult(
        status=rowcount,  # Use status for rowcount
        headers={"rowcount": str(rowcount)},
    )
