"""
Dashboard data generator.

Scans cassette directories and builds data for the dashboard view.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CassetteSummary:
    """Summary of a single cassette for dashboard display."""

    path: str
    filename: str
    method: str
    endpoint: str
    status: int
    duration_ms: float
    recorded_at: str
    event_count: int
    is_error: bool
    service: str = ""
    env: str = ""

    # For expandable details
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error_info: dict[str, Any] | None = None  # Stack trace, error type, message

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "filename": self.filename,
            "method": self.method,
            "endpoint": self.endpoint,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "recorded_at": self.recorded_at,
            "event_count": self.event_count,
            "is_error": self.is_error,
            "service": self.service,
            "env": self.env,
            "request_headers": self.request_headers,
            "response_headers": self.response_headers,
            "events": self.events,
            "error_info": self.error_info,
        }


@dataclass
class DashboardData:
    """Complete dashboard data for rendering."""

    title: str
    cassette_dir: str
    generated_at: str
    cassettes: list[CassetteSummary] = field(default_factory=list)

    # Stats
    total_count: int = 0
    error_count: int = 0
    success_count: int = 0

    # Unique values for filters
    methods: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    statuses: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON/template use."""
        return {
            "title": self.title,
            "cassette_dir": self.cassette_dir,
            "generated_at": self.generated_at,
            "cassettes": [c.to_dict() for c in self.cassettes],
            "stats": {
                "total": self.total_count,
                "errors": self.error_count,
                "success": self.success_count,
            },
            "filters": {
                "methods": self.methods,
                "endpoints": self.endpoints,
                "statuses": self.statuses,
            },
        }


def generate_dashboard(cassette_dir: str, limit: int = 500) -> DashboardData:
    """
    Generate dashboard data from a cassette directory.

    Args:
        cassette_dir: Path to the cassettes directory.
        limit: Maximum number of cassettes to include.

    Returns:
        DashboardData ready for rendering.
    """
    from datetime import datetime

    dir_path = Path(cassette_dir).resolve()

    dashboard = DashboardData(
        title="Timetracer Dashboard",
        cassette_dir=str(dir_path),
        generated_at=datetime.now().isoformat(),
    )

    if not dir_path.exists():
        return dashboard

    # Find all cassette files
    cassette_files: list[tuple[Path, float]] = []
    for json_file in dir_path.rglob("*.json"):
        # Skip index files
        if json_file.name == "index.json":
            continue
        try:
            mtime = json_file.stat().st_mtime
            cassette_files.append((json_file, mtime))
        except OSError:
            continue

    # Sort by modification time (newest first)
    cassette_files.sort(key=lambda x: x[1], reverse=True)

    # Limit results
    cassette_files = cassette_files[:limit]

    # Track unique values for filters
    methods_set: set[str] = set()
    endpoints_set: set[str] = set()
    statuses_set: set[int] = set()

    # Process each cassette
    for file_path, _ in cassette_files:
        try:
            summary = _load_cassette_summary(file_path, dir_path)
            if summary:
                dashboard.cassettes.append(summary)

                # Track filters
                methods_set.add(summary.method)
                endpoints_set.add(summary.endpoint)
                statuses_set.add(summary.status)

                # Track stats
                if summary.is_error:
                    dashboard.error_count += 1
                else:
                    dashboard.success_count += 1
        except Exception:
            # Skip malformed cassettes
            continue

    dashboard.total_count = len(dashboard.cassettes)
    dashboard.methods = sorted(methods_set)
    dashboard.endpoints = sorted(endpoints_set)
    dashboard.statuses = sorted(statuses_set)

    return dashboard


def _load_cassette_summary(file_path: Path, base_dir: Path) -> CassetteSummary | None:
    """Load a cassette file and extract summary data."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Extract request info
    request = data.get("request", {})
    response = data.get("response", {})
    session = data.get("session", {})
    events = data.get("events", [])

    method = request.get("method", "UNKNOWN")
    path = request.get("route_template") or request.get("path", "/unknown")
    status = response.get("status", 0)
    duration_ms = response.get("duration_ms", 0)
    recorded_at = session.get("recorded_at", "")

    # Extract headers (redacted versions are fine)
    req_headers = request.get("headers", {})
    res_headers = response.get("headers", {})

    # Build event summaries
    event_summaries = []
    for event in events:
        sig = event.get("signature", {})
        result = event.get("result", {})
        event_summaries.append({
            "type": event.get("event_type", "unknown"),
            "method": sig.get("method", ""),
            "url": sig.get("url", ""),
            "status": result.get("status"),
            "duration_ms": event.get("duration_ms", 0),
        })

    # Extract error info if present
    error_info = data.get("error_info")

    return CassetteSummary(
        path=str(file_path),
        filename=file_path.name,
        method=method,
        endpoint=path,
        status=status,
        duration_ms=duration_ms,
        recorded_at=recorded_at,
        event_count=len(events),
        is_error=status >= 400,
        service=session.get("service", ""),
        env=session.get("env", ""),
        request_headers=req_headers if isinstance(req_headers, dict) else {},
        response_headers=res_headers if isinstance(res_headers, dict) else {},
        events=event_summaries,
        error_info=error_info,
    )
