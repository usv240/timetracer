"""
Motor (async MongoDB) plugin for Timetracer.

Captures and replays Motor/MongoDB async database operations.
This enables recording MongoDB interactions for deterministic replay.

Usage:
    from timetracer.plugins import enable_motor

    enable_motor()  # Enable globally
    # or
    enable_motor(client)  # Enable for specific client
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
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# Store original methods for restoration
_original_methods: dict[str, Callable] = {}
_enabled = False


def enable_motor(client: "AsyncIOMotorClient | None" = None) -> None:
    """
    Enable Motor/MongoDB interception for recording and replay.

    This patches Motor collection methods to capture database operations.
    Call disable_motor() to restore original behavior.

    Args:
        client: Optional specific client. If None, patches globally.
    """
    global _enabled

    if _enabled:
        return

    try:
        from motor.motor_asyncio import AsyncIOMotorCollection
    except ImportError:
        raise ImportError(
            "motor is required for the motor plugin. "
            "Install it with: pip install motor"
        )

    # Store original methods
    _original_methods["find"] = AsyncIOMotorCollection.find
    _original_methods["find_one"] = AsyncIOMotorCollection.find_one
    _original_methods["insert_one"] = AsyncIOMotorCollection.insert_one
    _original_methods["insert_many"] = AsyncIOMotorCollection.insert_many
    _original_methods["update_one"] = AsyncIOMotorCollection.update_one
    _original_methods["update_many"] = AsyncIOMotorCollection.update_many
    _original_methods["delete_one"] = AsyncIOMotorCollection.delete_one
    _original_methods["delete_many"] = AsyncIOMotorCollection.delete_many
    _original_methods["aggregate"] = AsyncIOMotorCollection.aggregate
    _original_methods["count_documents"] = AsyncIOMotorCollection.count_documents

    # Patch methods
    AsyncIOMotorCollection.find = _patched_find
    AsyncIOMotorCollection.find_one = _patched_find_one
    AsyncIOMotorCollection.insert_one = _patched_insert_one
    AsyncIOMotorCollection.insert_many = _patched_insert_many
    AsyncIOMotorCollection.update_one = _patched_update_one
    AsyncIOMotorCollection.update_many = _patched_update_many
    AsyncIOMotorCollection.delete_one = _patched_delete_one
    AsyncIOMotorCollection.delete_many = _patched_delete_many
    AsyncIOMotorCollection.aggregate = _patched_aggregate
    AsyncIOMotorCollection.count_documents = _patched_count_documents

    _enabled = True


def disable_motor() -> None:
    """
    Disable Motor/MongoDB interception and restore original behavior.
    """
    global _enabled

    if not _enabled:
        return

    try:
        from motor.motor_asyncio import AsyncIOMotorCollection
    except ImportError:
        return

    # Restore original methods
    if "find" in _original_methods:
        AsyncIOMotorCollection.find = _original_methods["find"]
    if "find_one" in _original_methods:
        AsyncIOMotorCollection.find_one = _original_methods["find_one"]
    if "insert_one" in _original_methods:
        AsyncIOMotorCollection.insert_one = _original_methods["insert_one"]
    if "insert_many" in _original_methods:
        AsyncIOMotorCollection.insert_many = _original_methods["insert_many"]
    if "update_one" in _original_methods:
        AsyncIOMotorCollection.update_one = _original_methods["update_one"]
    if "update_many" in _original_methods:
        AsyncIOMotorCollection.update_many = _original_methods["update_many"]
    if "delete_one" in _original_methods:
        AsyncIOMotorCollection.delete_one = _original_methods["delete_one"]
    if "delete_many" in _original_methods:
        AsyncIOMotorCollection.delete_many = _original_methods["delete_many"]
    if "aggregate" in _original_methods:
        AsyncIOMotorCollection.aggregate = _original_methods["aggregate"]
    if "count_documents" in _original_methods:
        AsyncIOMotorCollection.count_documents = _original_methods["count_documents"]

    _original_methods.clear()
    _enabled = False


# =============================================================================
# Patched Methods
# =============================================================================

def _patched_find(
    self: "AsyncIOMotorCollection",
    filter: dict | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched find method - note: find() returns a cursor, not awaitable."""
    # Find returns a cursor, we record it but can't easily time it
    # The actual query happens when iterating
    if has_active_session():
        session = get_current_session()
        if session.is_recording:
            _record_operation(
                collection=self,
                operation="find",
                filter_doc=filter,
                result_data={"type": "cursor"},
                duration_ms=0,  # Cursor creation is instant
            )

    return _original_methods["find"](self, filter, *args, **kwargs)


async def _patched_find_one(
    self: "AsyncIOMotorCollection",
    filter: dict | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched find_one method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["find_one"](self, filter, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="find_one",
                    filter_doc=filter,
                    result_data=result,
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_insert_one(
    self: "AsyncIOMotorCollection",
    document: dict,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched insert_one method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["insert_one"](self, document, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="insert_one",
                    filter_doc=document,
                    result_data={
                        "inserted_id": str(result.inserted_id) if result else None,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_insert_many(
    self: "AsyncIOMotorCollection",
    documents: list[dict],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched insert_many method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["insert_many"](self, documents, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="insert_many",
                    filter_doc={"count": len(documents)},
                    result_data={
                        "inserted_count": len(result.inserted_ids) if result else 0,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_update_one(
    self: "AsyncIOMotorCollection",
    filter: dict,
    update: dict,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched update_one method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["update_one"](self, filter, update, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="update_one",
                    filter_doc=filter,
                    update_doc=update,
                    result_data={
                        "matched_count": result.matched_count if result else 0,
                        "modified_count": result.modified_count if result else 0,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_update_many(
    self: "AsyncIOMotorCollection",
    filter: dict,
    update: dict,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched update_many method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["update_many"](self, filter, update, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="update_many",
                    filter_doc=filter,
                    update_doc=update,
                    result_data={
                        "matched_count": result.matched_count if result else 0,
                        "modified_count": result.modified_count if result else 0,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_delete_one(
    self: "AsyncIOMotorCollection",
    filter: dict,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched delete_one method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["delete_one"](self, filter, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="delete_one",
                    filter_doc=filter,
                    result_data={
                        "deleted_count": result.deleted_count if result else 0,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


async def _patched_delete_many(
    self: "AsyncIOMotorCollection",
    filter: dict,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched delete_many method."""
    start_time = time.perf_counter()
    error_info = None
    result = None

    try:
        result = await _original_methods["delete_many"](self, filter, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="delete_many",
                    filter_doc=filter,
                    result_data={
                        "deleted_count": result.deleted_count if result else 0,
                        "acknowledged": result.acknowledged if result else False,
                    },
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


def _patched_aggregate(
    self: "AsyncIOMotorCollection",
    pipeline: list[dict],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Patched aggregate method - returns cursor."""
    if has_active_session():
        session = get_current_session()
        if session.is_recording:
            _record_operation(
                collection=self,
                operation="aggregate",
                filter_doc={"pipeline_stages": len(pipeline)},
                result_data={"type": "cursor"},
                duration_ms=0,
            )

    return _original_methods["aggregate"](self, pipeline, *args, **kwargs)


async def _patched_count_documents(
    self: "AsyncIOMotorCollection",
    filter: dict,
    *args: Any,
    **kwargs: Any,
) -> int:
    """Patched count_documents method."""
    start_time = time.perf_counter()
    error_info = None
    result = 0

    try:
        result = await _original_methods["count_documents"](self, filter, *args, **kwargs)
        return result
    except Exception as e:
        error_info = (type(e).__name__, str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if has_active_session():
            session = get_current_session()
            if session.is_recording:
                _record_operation(
                    collection=self,
                    operation="count_documents",
                    filter_doc=filter,
                    result_data={"count": result},
                    duration_ms=duration_ms,
                    error_info=error_info,
                )


# =============================================================================
# Event Building
# =============================================================================

def _record_operation(
    collection: "AsyncIOMotorCollection",
    operation: str,
    filter_doc: dict | None = None,
    update_doc: dict | None = None,
    result_data: Any = None,
    duration_ms: float = 0,
    error_info: tuple[str, str] | None = None,
) -> None:
    """Record a MongoDB operation as an event."""
    from timetracer.session import TraceSession

    session = get_current_session()
    if not isinstance(session, TraceSession):
        return

    # Get collection info
    db_name = collection.database.name
    collection_name = collection.name

    # Calculate start offset
    start_offset = session.elapsed_ms if hasattr(session, 'elapsed_ms') else 0

    # Build event
    event = _build_event(
        operation=operation,
        db_name=db_name,
        collection_name=collection_name,
        filter_doc=filter_doc,
        update_doc=update_doc,
        result_data=result_data,
        start_offset_ms=start_offset,
        duration_ms=duration_ms,
        error_info=error_info,
    )

    session.add_event(event)


def _build_event(
    operation: str,
    db_name: str,
    collection_name: str,
    filter_doc: dict | None,
    update_doc: dict | None,
    result_data: Any,
    start_offset_ms: float,
    duration_ms: float,
    error_info: tuple[str, str] | None,
) -> DependencyEvent:
    """Build a DependencyEvent from MongoDB operation."""
    signature = _make_signature(
        operation=operation,
        db_name=db_name,
        collection_name=collection_name,
        filter_doc=filter_doc,
        update_doc=update_doc,
    )

    result = _make_result(result_data, error_info)

    return DependencyEvent(
        eid=0,  # Will be set by session
        event_type=EventType.DB_QUERY,
        start_offset_ms=start_offset_ms,
        duration_ms=duration_ms,
        signature=signature,
        result=result,
    )


def _make_signature(
    operation: str,
    db_name: str,
    collection_name: str,
    filter_doc: dict | None,
    update_doc: dict | None,
) -> EventSignature:
    """Create EventSignature from MongoDB operation."""
    # Create a query dict with filter info
    query = {}
    if filter_doc:
        # Only include keys, not values (for matching flexibility)
        query["filter_keys"] = sorted(filter_doc.keys()) if isinstance(filter_doc, dict) else []

    # Hash the filter and update documents
    body_parts = []
    if filter_doc:
        try:
            body_parts.append(("filter", _safe_serialize(filter_doc)))
        except Exception:
            pass
    if update_doc:
        try:
            body_parts.append(("update", _safe_serialize(update_doc)))
        except Exception:
            pass

    body_hash = None
    if body_parts:
        body_hash = hash_body(str(body_parts))

    return EventSignature(
        lib="motor",
        method=operation.upper(),  # FIND_ONE, INSERT_ONE, etc.
        url=f"{db_name}.{collection_name}",  # db.collection
        query=query,
        body_hash=body_hash,
    )


def _safe_serialize(doc: Any) -> str:
    """Safely serialize a MongoDB document to string."""
    import json

    from bson import ObjectId

    def default_serializer(obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return str(obj)

    try:
        return json.dumps(doc, default=default_serializer, sort_keys=True)
    except Exception:
        return str(doc)


def _make_result(
    result_data: Any,
    error_info: tuple[str, str] | None,
) -> EventResult:
    """Create EventResult from MongoDB operation result."""
    body = None
    if result_data:
        body = BodySnapshot(
            captured=True,
            encoding="utf-8",
            data=result_data if isinstance(result_data, dict) else {"value": result_data},
            truncated=False,
            size_bytes=None,
            hash=None,
        )

    return EventResult(
        status=0 if error_info is None else -1,
        headers={},
        body=body,
        error=error_info[1] if error_info else None,
        error_type=error_info[0] if error_info else None,
    )
