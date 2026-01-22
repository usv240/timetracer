"""
Cassette I/O - reading and writing cassette files.

Handles serialization, deserialization, and file management.
Supports gzip compression for smaller storage.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from timetracer.cassette.naming import cassette_filename, get_date_directory
from timetracer.constants import SCHEMA_VERSION, CompressionType, EventType
from timetracer.exceptions import CassetteNotFoundError, CassetteSchemaError
from timetracer.types import (
    AppliedPolicies,
    BodySnapshot,
    CaptureStats,
    Cassette,
    DependencyEvent,
    EventResult,
    EventSignature,
    RequestSnapshot,
    ResponseSnapshot,
    SessionMeta,
)

if TYPE_CHECKING:
    from timetracer.config import TraceConfig
    from timetracer.session import TraceSession


class CassetteEncoder(json.JSONEncoder):
    """Custom JSON encoder for cassette data."""

    def default(self, obj: Any) -> Any:
        # Handle dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)

        # Handle enums
        if hasattr(obj, "value"):
            return obj.value

        return super().default(obj)


def write_cassette(session: TraceSession, config: TraceConfig) -> str:
    """
    Write a trace session to a cassette file.

    Creates date-based subdirectory and uses standardized naming.
    Supports gzip compression when config.compression is set to GZIP.

    Args:
        session: The completed trace session.
        config: Configuration for cassette directory and compression.

    Returns:
        Absolute path to the written cassette file.
    """
    # Ensure session is finalized
    if not session._finalized:
        session.finalize()

    # Convert to cassette
    cassette = session.to_cassette()

    # Build path
    base_dir = Path(config.cassette_dir).resolve()
    date_dir = base_dir / get_date_directory()
    date_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    method = cassette.request.method or "UNKNOWN"
    route = cassette.request.route_template or cassette.request.path or "unknown"
    filename = cassette_filename(method, route, session.session_id)

    # Add .gz extension if using gzip compression
    if config.compression == CompressionType.GZIP:
        filename = filename + ".gz"

    file_path = date_dir / filename

    # Serialize and write
    cassette_dict = _cassette_to_dict(cassette)
    json_content = json.dumps(cassette_dict, indent=2, cls=CassetteEncoder)

    if config.compression == CompressionType.GZIP:
        # Write gzip compressed
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            f.write(json_content)
    else:
        # Write uncompressed
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_content)

    return str(file_path)


def read_cassette(path: str) -> Cassette:
    """
    Read a cassette from file.

    Automatically detects gzip compression by file extension (.json.gz).

    Args:
        path: Path to the cassette file (.json or .json.gz).

    Returns:
        Loaded Cassette object.

    Raises:
        CassetteNotFoundError: If file doesn't exist.
        CassetteSchemaError: If schema version is incompatible.
    """
    from timetracer.constants import SUPPORTED_SCHEMA_VERSIONS

    file_path = Path(path)

    if not file_path.exists():
        raise CassetteNotFoundError(path)

    # Auto-detect gzip by file extension
    is_gzip = file_path.suffix == ".gz" or str(file_path).endswith(".json.gz")

    if is_gzip:
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    # Validate schema version
    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise CassetteSchemaError(path, SCHEMA_VERSION, schema_version)

    # Migrate if needed
    if schema_version != SCHEMA_VERSION:
        data = _migrate_cassette(data, schema_version)

    return _dict_to_cassette(data)


def _migrate_cassette(data: dict[str, Any], from_version: str) -> dict[str, Any]:
    """
    Migrate cassette from older schema version to current.

    Args:
        data: Cassette data dict.
        from_version: Current schema version of the data.

    Returns:
        Migrated cassette data dict.
    """
    # v0.1 -> v1.0 migration
    if from_version == "0.1":
        # Schema 0.1 and 1.0 are compatible - just update version
        data["schema_version"] = SCHEMA_VERSION

    return data


def _cassette_to_dict(cassette: Cassette) -> dict[str, Any]:
    """Convert Cassette to a dictionary for JSON serialization."""
    return {
        "schema_version": cassette.schema_version,
        "session": _session_meta_to_dict(cassette.session),
        "request": _request_to_dict(cassette.request),
        "response": _response_to_dict(cassette.response),
        "events": [_event_to_dict(e) for e in cassette.events],
        "policies": _policies_to_dict(cassette.policies),
        "stats": _stats_to_dict(cassette.stats),
    }


def _session_meta_to_dict(meta: SessionMeta) -> dict[str, Any]:
    """Convert SessionMeta to dict."""
    return {
        "id": meta.id,
        "recorded_at": meta.recorded_at,
        "service": meta.service,
        "env": meta.env,
        "framework": meta.framework,
        "timetracer_version": meta.timetracer_version,
        "python_version": meta.python_version,
        "git_sha": meta.git_sha,
    }


def _request_to_dict(req: RequestSnapshot) -> dict[str, Any]:
    """Convert RequestSnapshot to dict."""
    result: dict[str, Any] = {
        "method": req.method,
        "path": req.path,
    }
    if req.route_template:
        result["route_template"] = req.route_template
    if req.headers:
        result["headers"] = req.headers
    if req.query:
        result["query"] = req.query
    if req.body:
        result["body"] = _body_to_dict(req.body)
    if req.client_ip:
        result["client_ip"] = req.client_ip
    if req.user_agent:
        result["user_agent"] = req.user_agent
    return result


def _response_to_dict(res: ResponseSnapshot) -> dict[str, Any]:
    """Convert ResponseSnapshot to dict."""
    result: dict[str, Any] = {
        "status": res.status,
        "duration_ms": res.duration_ms,
    }
    if res.headers:
        result["headers"] = res.headers
    if res.body:
        result["body"] = _body_to_dict(res.body)
    return result


def _body_to_dict(body: BodySnapshot) -> dict[str, Any]:
    """Convert BodySnapshot to dict."""
    result: dict[str, Any] = {"_captured": body.captured}
    if body.encoding:
        result["encoding"] = body.encoding
    if body.data is not None:
        result["data"] = body.data
    if body.truncated:
        result["truncated"] = body.truncated
    if body.size_bytes is not None:
        result["size_bytes"] = body.size_bytes
    if body.hash:
        result["hash"] = body.hash
    return result


def _event_to_dict(event: DependencyEvent) -> dict[str, Any]:
    """Convert DependencyEvent to dict."""
    return {
        "eid": event.eid,
        "type": event.event_type.value,
        "start_offset_ms": event.start_offset_ms,
        "duration_ms": event.duration_ms,
        "signature": _signature_to_dict(event.signature),
        "result": _result_to_dict(event.result),
    }


def _signature_to_dict(sig: EventSignature) -> dict[str, Any]:
    """Convert EventSignature to dict."""
    result: dict[str, Any] = {
        "lib": sig.lib,
        "method": sig.method,
    }
    if sig.url:
        result["url"] = sig.url
    if sig.query:
        result["query"] = sig.query
    if sig.headers_hash:
        result["headers_hash"] = sig.headers_hash
    if sig.body_hash:
        result["body_hash"] = sig.body_hash
    return result


def _result_to_dict(result: EventResult) -> dict[str, Any]:
    """Convert EventResult to dict."""
    data: dict[str, Any] = {}
    if result.status is not None:
        data["status"] = result.status
    if result.headers:
        data["headers"] = result.headers
    if result.body:
        data["body"] = _body_to_dict(result.body)
    if result.error:
        data["error"] = result.error
    if result.error_type:
        data["error_type"] = result.error_type
    return data


def _policies_to_dict(policies: AppliedPolicies) -> dict[str, Any]:
    """Convert AppliedPolicies to dict."""
    return {
        "redaction": {
            "mode": policies.redaction_mode,
            "rules": policies.redaction_rules,
        },
        "capture": {
            "max_body_kb": policies.max_body_kb,
            "store_request_body": policies.store_request_body,
            "store_response_body": policies.store_response_body,
        },
        "sampling": {
            "rate": policies.sample_rate,
            "errors_only": policies.errors_only,
        },
    }


def _stats_to_dict(stats: CaptureStats) -> dict[str, Any]:
    """Convert CaptureStats to dict."""
    return {
        "event_counts": stats.event_counts,
        "total_events": stats.total_events,
        "total_duration_ms": stats.total_duration_ms,
    }


# =============================================================================
# DESERIALIZATION (dict -> Cassette)
# =============================================================================

def _dict_to_cassette(data: dict[str, Any]) -> Cassette:
    """Convert dict to Cassette."""
    return Cassette(
        schema_version=data["schema_version"],
        session=_dict_to_session_meta(data["session"]),
        request=_dict_to_request(data["request"]),
        response=_dict_to_response(data["response"]),
        events=[_dict_to_event(e) for e in data.get("events", [])],
        policies=_dict_to_policies(data.get("policies", {})),
        stats=_dict_to_stats(data.get("stats", {})),
    )


def _dict_to_session_meta(data: dict[str, Any]) -> SessionMeta:
    """Convert dict to SessionMeta."""
    return SessionMeta(
        id=data["id"],
        recorded_at=data["recorded_at"],
        service=data.get("service", ""),
        env=data.get("env", ""),
        framework=data.get("framework", "fastapi"),
        timetracer_version=data.get("timetracer_version") or data.get("timetrace_version", ""),
        python_version=data.get("python_version", ""),
        git_sha=data.get("git_sha"),
    )


def _dict_to_request(data: dict[str, Any]) -> RequestSnapshot:
    """Convert dict to RequestSnapshot."""
    return RequestSnapshot(
        method=data["method"],
        path=data["path"],
        route_template=data.get("route_template"),
        headers=data.get("headers", {}),
        query=data.get("query", {}),
        body=_dict_to_body(data["body"]) if "body" in data else None,
        client_ip=data.get("client_ip"),
        user_agent=data.get("user_agent"),
    )


def _dict_to_response(data: dict[str, Any]) -> ResponseSnapshot:
    """Convert dict to ResponseSnapshot."""
    return ResponseSnapshot(
        status=data["status"],
        headers=data.get("headers", {}),
        body=_dict_to_body(data["body"]) if "body" in data else None,
        duration_ms=data.get("duration_ms", 0.0),
    )


def _dict_to_body(data: dict[str, Any]) -> BodySnapshot:
    """Convert dict to BodySnapshot."""
    return BodySnapshot(
        captured=data.get("_captured", False),
        encoding=data.get("encoding"),
        data=data.get("data"),
        truncated=data.get("truncated", False),
        size_bytes=data.get("size_bytes"),
        hash=data.get("hash"),
    )


def _dict_to_event(data: dict[str, Any]) -> DependencyEvent:
    """Convert dict to DependencyEvent."""
    return DependencyEvent(
        eid=data["eid"],
        event_type=EventType(data["type"]),
        start_offset_ms=data["start_offset_ms"],
        duration_ms=data["duration_ms"],
        signature=_dict_to_signature(data["signature"]),
        result=_dict_to_result(data.get("result", {})),
    )


def _dict_to_signature(data: dict[str, Any]) -> EventSignature:
    """Convert dict to EventSignature."""
    return EventSignature(
        lib=data["lib"],
        method=data["method"],
        url=data.get("url"),
        query=data.get("query", {}),
        headers_hash=data.get("headers_hash"),
        body_hash=data.get("body_hash"),
    )


def _dict_to_result(data: dict[str, Any]) -> EventResult:
    """Convert dict to EventResult."""
    return EventResult(
        status=data.get("status"),
        headers=data.get("headers", {}),
        body=_dict_to_body(data["body"]) if "body" in data else None,
        error=data.get("error"),
        error_type=data.get("error_type"),
    )


def _dict_to_policies(data: dict[str, Any]) -> AppliedPolicies:
    """Convert dict to AppliedPolicies."""
    redaction = data.get("redaction", {})
    capture = data.get("capture", {})
    sampling = data.get("sampling", {})

    return AppliedPolicies(
        redaction_mode=redaction.get("mode", "default"),
        redaction_rules=redaction.get("rules", []),
        max_body_kb=capture.get("max_body_kb", 64),
        store_request_body=capture.get("store_request_body", "on_error"),
        store_response_body=capture.get("store_response_body", "on_error"),
        sample_rate=sampling.get("rate", 1.0),
        errors_only=sampling.get("errors_only", False),
    )


def _dict_to_stats(data: dict[str, Any]) -> CaptureStats:
    """Convert dict to CaptureStats."""
    return CaptureStats(
        event_counts=data.get("event_counts", {}),
        total_events=data.get("total_events", 0),
        total_duration_ms=data.get("total_duration_ms", 0.0),
    )
