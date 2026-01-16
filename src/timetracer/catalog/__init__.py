"""
Cassette catalog and search functionality.

Provides indexing and search capabilities for cassettes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CassetteEntry:
    """A single cassette index entry."""
    path: str
    method: str
    endpoint: str
    route_template: str | None
    status: int
    duration_ms: float
    recorded_at: str
    service: str
    env: str
    event_count: int
    has_errors: bool
    size_bytes: int

    def matches(self, query: "SearchQuery") -> bool:
        """Check if entry matches search query."""
        if query.method and query.method.upper() != self.method.upper():
            return False

        if query.endpoint and query.endpoint.lower() not in self.endpoint.lower():
            return False

        if query.status_min and self.status < query.status_min:
            return False

        if query.status_max and self.status > query.status_max:
            return False

        if query.errors_only and not self.has_errors:
            return False

        if query.service and query.service.lower() != self.service.lower():
            return False

        if query.env and query.env.lower() != self.env.lower():
            return False

        if query.date_from:
            try:
                recorded = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
                if recorded < query.date_from:
                    return False
            except Exception:
                pass

        if query.date_to:
            try:
                recorded = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
                if recorded > query.date_to:
                    return False
            except Exception:
                pass

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "method": self.method,
            "endpoint": self.endpoint,
            "route_template": self.route_template,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "recorded_at": self.recorded_at,
            "service": self.service,
            "env": self.env,
            "event_count": self.event_count,
            "has_errors": self.has_errors,
            "size_bytes": self.size_bytes,
        }


@dataclass
class SearchQuery:
    """Search query parameters."""
    method: str | None = None
    endpoint: str | None = None
    status_min: int | None = None
    status_max: int | None = None
    errors_only: bool = False
    service: str | None = None
    env: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 50


@dataclass
class CassetteIndex:
    """Index of all cassettes in a directory."""
    entries: list[CassetteEntry] = field(default_factory=list)
    indexed_at: str = ""
    cassette_dir: str = ""
    total_count: int = 0

    def search(self, query: SearchQuery) -> list[CassetteEntry]:
        """Search cassettes matching query."""
        results = []
        for entry in self.entries:
            if entry.matches(query):
                results.append(entry)
                if len(results) >= query.limit:
                    break
        return results

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "indexed_at": self.indexed_at,
            "cassette_dir": self.cassette_dir,
            "total_count": self.total_count,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CassetteIndex":
        """Create from dictionary."""
        entries = [
            CassetteEntry(**e) for e in data.get("entries", [])
        ]
        return cls(
            entries=entries,
            indexed_at=data.get("indexed_at", ""),
            cassette_dir=data.get("cassette_dir", ""),
            total_count=data.get("total_count", len(entries)),
        )


def build_index(
    cassette_dir: str,
    recursive: bool = True,
) -> CassetteIndex:
    """
    Build an index of all cassettes in a directory.

    Args:
        cassette_dir: Directory containing cassettes.
        recursive: Search subdirectories.

    Returns:
        CassetteIndex with all cassette entries.
    """
    dir_path = Path(cassette_dir)

    if not dir_path.exists():
        return CassetteIndex(
            cassette_dir=cassette_dir,
            indexed_at=datetime.utcnow().isoformat() + "Z",
        )

    entries = []
    pattern = "**/*.json" if recursive else "*.json"

    for json_file in dir_path.glob(pattern):
        try:
            entry = _index_cassette(json_file, dir_path)
            if entry:
                entries.append(entry)
        except Exception:
            # Skip invalid files
            continue

    # Sort by recorded_at (newest first)
    entries.sort(key=lambda e: e.recorded_at, reverse=True)

    return CassetteIndex(
        entries=entries,
        indexed_at=datetime.utcnow().isoformat() + "Z",
        cassette_dir=cassette_dir,
        total_count=len(entries),
    )


def _index_cassette(path: Path, base_dir: Path) -> CassetteEntry | None:
    """Extract index entry from a cassette file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    # Validate it's a timetrace cassette
    if "schema_version" not in data:
        return None

    request = data.get("request", {})
    response = data.get("response", {})
    session = data.get("session", {})
    events = data.get("events", [])

    method = request.get("method", "UNKNOWN")
    endpoint = request.get("path", "/")
    route_template = request.get("route_template")
    status = response.get("status", 0)
    duration_ms = response.get("duration_ms", 0)
    recorded_at = session.get("recorded_at", "")
    service = session.get("service", "")
    env = session.get("env", "")

    return CassetteEntry(
        path=str(path.relative_to(base_dir)),
        method=method,
        endpoint=endpoint,
        route_template=route_template,
        status=status,
        duration_ms=duration_ms,
        recorded_at=recorded_at,
        service=service,
        env=env,
        event_count=len(events),
        has_errors=status >= 400,
        size_bytes=path.stat().st_size,
    )


def save_index(index: CassetteIndex, output_path: str) -> None:
    """Save index to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index.to_dict(), f, indent=2)


def load_index(path: str) -> CassetteIndex:
    """Load index from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CassetteIndex.from_dict(data)


def search_cassettes(
    cassette_dir: str,
    method: str | None = None,
    endpoint: str | None = None,
    status_min: int | None = None,
    status_max: int | None = None,
    errors_only: bool = False,
    service: str | None = None,
    env: str | None = None,
    limit: int = 50,
) -> list[CassetteEntry]:
    """
    Search cassettes in a directory.

    Args:
        cassette_dir: Directory containing cassettes.
        method: Filter by HTTP method (GET, POST, etc.).
        endpoint: Filter by endpoint path (partial match).
        status_min: Minimum status code.
        status_max: Maximum status code.
        errors_only: Only return error responses (4xx, 5xx).
        service: Filter by service name.
        env: Filter by environment.
        limit: Maximum results.

    Returns:
        List of matching CassetteEntry objects.
    """
    index = build_index(cassette_dir)

    query = SearchQuery(
        method=method,
        endpoint=endpoint,
        status_min=status_min,
        status_max=status_max,
        errors_only=errors_only,
        service=service,
        env=env,
        limit=limit,
    )

    return index.search(query)
