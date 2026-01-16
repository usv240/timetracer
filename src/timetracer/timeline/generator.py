"""
Timeline data generator.

Converts cassette data into timeline-friendly format for visualization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from timetracer.cassette import read_cassette
from timetracer.types import Cassette


@dataclass
class TimelineEvent:
    """A single event on the timeline."""
    id: int
    label: str
    event_type: str
    start_ms: float
    duration_ms: float
    end_ms: float
    status: int | None = None
    url: str | None = None
    is_error: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineData:
    """Complete timeline data for visualization."""
    title: str
    method: str
    path: str
    total_duration_ms: float
    recorded_at: str

    # Main request span
    request_start: float = 0.0
    request_end: float = 0.0
    response_status: int = 0

    # All events
    events: list[TimelineEvent] = field(default_factory=list)

    # Stats
    event_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON/template use."""
        return {
            "title": self.title,
            "method": self.method,
            "path": self.path,
            "total_duration_ms": self.total_duration_ms,
            "recorded_at": self.recorded_at,
            "request": {
                "start": self.request_start,
                "end": self.request_end,
                "status": self.response_status,
            },
            "events": [
                {
                    "id": e.id,
                    "label": e.label,
                    "type": e.event_type,
                    "start_ms": e.start_ms,
                    "duration_ms": e.duration_ms,
                    "end_ms": e.end_ms,
                    "status": e.status,
                    "url": e.url,
                    "is_error": e.is_error,
                }
                for e in self.events
            ],
            "stats": {
                "event_count": self.event_count,
                "error_count": self.error_count,
            },
        }


def generate_timeline(cassette_path: str) -> TimelineData:
    """
    Generate timeline data from a cassette file.

    Args:
        cassette_path: Path to the cassette file.

    Returns:
        TimelineData ready for visualization.
    """
    cassette = read_cassette(cassette_path)
    return _cassette_to_timeline(cassette)


def _cassette_to_timeline(cassette: Cassette) -> TimelineData:
    """Convert Cassette to TimelineData."""
    req = cassette.request
    res = cassette.response

    timeline = TimelineData(
        title=f"{req.method} {req.path}",
        method=req.method,
        path=req.path,
        total_duration_ms=res.duration_ms,
        recorded_at=cassette.session.recorded_at,
        request_start=0.0,
        request_end=res.duration_ms,
        response_status=res.status,
    )

    # Convert events
    error_count = 0
    for event in cassette.events:
        is_error = (event.result.status or 0) >= 400 or event.result.error is not None
        if is_error:
            error_count += 1

        # Create label
        sig = event.signature
        if sig.url:
            # Shorten URL for display
            url_short = sig.url
            if len(url_short) > 50:
                url_short = url_short[:47] + "..."
            label = f"{sig.method} {url_short}"
        else:
            label = f"{event.event_type.value}"

        timeline_event = TimelineEvent(
            id=event.eid,
            label=label,
            event_type=event.event_type.value,
            start_ms=event.start_offset_ms,
            duration_ms=event.duration_ms,
            end_ms=event.start_offset_ms + event.duration_ms,
            status=event.result.status,
            url=sig.url,
            is_error=is_error,
        )
        timeline.events.append(timeline_event)

    timeline.event_count = len(timeline.events)
    timeline.error_count = error_count

    return timeline
