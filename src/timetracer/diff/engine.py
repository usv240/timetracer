"""
Diff engine for comparing cassettes.

Compares two cassettes and produces a detailed report of differences.
Useful for regression detection and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from timetracer.cassette import read_cassette
from timetracer.types import Cassette, DependencyEvent


@dataclass
class EventDiff:
    """Difference between two events."""
    event_index: int
    event_type: str

    # What changed
    status_changed: bool = False
    old_status: int | None = None
    new_status: int | None = None

    duration_changed: bool = False
    old_duration_ms: float = 0.0
    new_duration_ms: float = 0.0
    duration_delta_ms: float = 0.0
    duration_delta_pct: float = 0.0

    url_changed: bool = False
    old_url: str | None = None
    new_url: str | None = None

    body_changed: bool = False

    # Is this a critical diff?
    is_critical: bool = False
    summary: str = ""


@dataclass
class ResponseDiff:
    """Difference between response data."""
    status_changed: bool = False
    old_status: int = 0
    new_status: int = 0

    duration_changed: bool = False
    old_duration_ms: float = 0.0
    new_duration_ms: float = 0.0
    duration_delta_ms: float = 0.0
    duration_delta_pct: float = 0.0

    body_changed: bool = False


@dataclass
class DiffReport:
    """Complete diff report between two cassettes."""
    cassette_a_path: str
    cassette_b_path: str

    # Request info
    method: str = ""
    path: str = ""

    # Overall result
    has_differences: bool = False
    is_regression: bool = False

    # Response diff
    response_diff: ResponseDiff = field(default_factory=ResponseDiff)

    # Event diffs
    event_count_a: int = 0
    event_count_b: int = 0
    event_count_changed: bool = False
    event_diffs: list[EventDiff] = field(default_factory=list)

    # Unmatched events
    extra_events_a: list[int] = field(default_factory=list)
    extra_events_b: list[int] = field(default_factory=list)

    # Summary stats
    total_duration_delta_ms: float = 0.0
    critical_diffs: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "cassette_a": self.cassette_a_path,
            "cassette_b": self.cassette_b_path,
            "request": {
                "method": self.method,
                "path": self.path,
            },
            "has_differences": self.has_differences,
            "is_regression": self.is_regression,
            "response": {
                "status_changed": self.response_diff.status_changed,
                "old_status": self.response_diff.old_status,
                "new_status": self.response_diff.new_status,
                "duration_delta_ms": self.response_diff.duration_delta_ms,
                "duration_delta_pct": self.response_diff.duration_delta_pct,
            },
            "events": {
                "count_a": self.event_count_a,
                "count_b": self.event_count_b,
                "count_changed": self.event_count_changed,
                "diffs": [
                    {
                        "index": d.event_index,
                        "type": d.event_type,
                        "summary": d.summary,
                        "is_critical": d.is_critical,
                    }
                    for d in self.event_diffs
                ],
                "extra_in_a": self.extra_events_a,
                "extra_in_b": self.extra_events_b,
            },
            "summary": {
                "total_duration_delta_ms": self.total_duration_delta_ms,
                "critical_diffs": self.critical_diffs,
            },
        }


def diff_cassettes(
    path_a: str,
    path_b: str,
    *,
    duration_threshold_pct: float = 20.0,
) -> DiffReport:
    """
    Compare two cassettes and produce a diff report.

    Args:
        path_a: Path to first cassette (baseline).
        path_b: Path to second cassette (comparison).
        duration_threshold_pct: Percentage change to flag as significant.

    Returns:
        DiffReport with all differences.
    """
    cassette_a = read_cassette(path_a)
    cassette_b = read_cassette(path_b)

    report = DiffReport(
        cassette_a_path=path_a,
        cassette_b_path=path_b,
        method=cassette_a.request.method,
        path=cassette_a.request.path,
    )

    # Compare response
    _compare_response(cassette_a, cassette_b, report, duration_threshold_pct)

    # Compare events
    _compare_events(cassette_a, cassette_b, report, duration_threshold_pct)

    # Determine overall status
    report.has_differences = (
        report.response_diff.status_changed
        or report.response_diff.duration_changed
        or report.event_count_changed
        or len(report.event_diffs) > 0
    )

    # Is it a regression? (status worsened or significant slowdown)
    report.is_regression = (
        (report.response_diff.status_changed and report.response_diff.new_status >= 400)
        or report.response_diff.duration_delta_pct > duration_threshold_pct
        or report.critical_diffs > 0
    )

    return report


def _compare_response(
    a: Cassette,
    b: Cassette,
    report: DiffReport,
    threshold_pct: float,
) -> None:
    """Compare response data."""
    res_a = a.response
    res_b = b.response

    diff = report.response_diff

    # Status
    if res_a.status != res_b.status:
        diff.status_changed = True
        diff.old_status = res_a.status
        diff.new_status = res_b.status

    # Duration
    diff.old_duration_ms = res_a.duration_ms
    diff.new_duration_ms = res_b.duration_ms
    diff.duration_delta_ms = res_b.duration_ms - res_a.duration_ms

    if res_a.duration_ms > 0:
        diff.duration_delta_pct = (diff.duration_delta_ms / res_a.duration_ms) * 100

    if abs(diff.duration_delta_pct) > threshold_pct:
        diff.duration_changed = True

    # Track total duration delta
    report.total_duration_delta_ms = diff.duration_delta_ms


def _compare_events(
    a: Cassette,
    b: Cassette,
    report: DiffReport,
    threshold_pct: float,
) -> None:
    """Compare dependency events."""
    events_a = a.events
    events_b = b.events

    report.event_count_a = len(events_a)
    report.event_count_b = len(events_b)
    report.event_count_changed = len(events_a) != len(events_b)

    # Compare events pairwise
    min_count = min(len(events_a), len(events_b))

    for i in range(min_count):
        event_a = events_a[i]
        event_b = events_b[i]

        diff = _compare_single_event(i, event_a, event_b, threshold_pct)
        if diff:
            report.event_diffs.append(diff)
            if diff.is_critical:
                report.critical_diffs += 1

    # Track extra events
    if len(events_a) > min_count:
        report.extra_events_a = list(range(min_count, len(events_a)))
    if len(events_b) > min_count:
        report.extra_events_b = list(range(min_count, len(events_b)))


def _compare_single_event(
    index: int,
    a: DependencyEvent,
    b: DependencyEvent,
    threshold_pct: float,
) -> EventDiff | None:
    """Compare two events at the same index."""
    diff = EventDiff(
        event_index=index,
        event_type=a.event_type.value,
    )

    has_diff = False
    summaries = []

    # Status change
    if a.result.status != b.result.status:
        diff.status_changed = True
        diff.old_status = a.result.status
        diff.new_status = b.result.status
        has_diff = True
        summaries.append(f"status: {a.result.status} → {b.result.status}")

        # Critical if went from success to error
        if (a.result.status or 0) < 400 and (b.result.status or 0) >= 400:
            diff.is_critical = True

    # Duration change
    diff.old_duration_ms = a.duration_ms
    diff.new_duration_ms = b.duration_ms
    diff.duration_delta_ms = b.duration_ms - a.duration_ms

    if a.duration_ms > 0:
        diff.duration_delta_pct = (diff.duration_delta_ms / a.duration_ms) * 100

    if abs(diff.duration_delta_pct) > threshold_pct:
        diff.duration_changed = True
        has_diff = True
        direction = "slower" if diff.duration_delta_ms > 0 else "faster"
        summaries.append(f"{abs(diff.duration_delta_pct):.0f}% {direction}")

    # URL change
    if a.signature.url != b.signature.url:
        diff.url_changed = True
        diff.old_url = a.signature.url
        diff.new_url = b.signature.url
        diff.is_critical = True
        has_diff = True
        summaries.append("URL changed")

    # Body change (by hash)
    if a.signature.body_hash != b.signature.body_hash:
        diff.body_changed = True
        has_diff = True
        summaries.append("request body changed")

    if not has_diff:
        return None

    diff.summary = "; ".join(summaries)
    return diff
