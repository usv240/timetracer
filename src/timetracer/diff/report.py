"""
Diff report formatting.

Provides human-readable output for diff reports.
"""

from __future__ import annotations

from timetracer.diff.engine import DiffReport


def format_diff_report(report: DiffReport, use_color: bool = True) -> str:
    """
    Format a diff report as human-readable text.

    Args:
        report: The diff report to format.
        use_color: Whether to include ANSI color codes.

    Returns:
        Formatted string.
    """
    lines = []

    # Header
    lines.append("")
    lines.append("=" * 70)
    lines.append("timetracer DIFF REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Files
    lines.append(f"Baseline:   {report.cassette_a_path}")
    lines.append(f"Comparison: {report.cassette_b_path}")
    lines.append("")

    # Request
    lines.append(f"Request: {report.method} {report.path}")
    lines.append("")

    # Overall result
    if report.is_regression:
        icon = "[FAIL]"
        status = "REGRESSION DETECTED"
    elif report.has_differences:
        icon = "[WARN]"
        status = "DIFFERENCES FOUND"
    else:
        icon = "[OK]"
        status = "NO DIFFERENCES"

    lines.append(f"{icon} {status}")
    lines.append("")

    # Response diff
    lines.append("-" * 40)
    lines.append("RESPONSE")
    lines.append("-" * 40)

    rd = report.response_diff

    if rd.status_changed:
        lines.append(f"  Status:   {rd.old_status} → {rd.new_status}")
    else:
        lines.append(f"  Status:   {rd.old_status} (unchanged)")

    if rd.duration_changed:
        direction = "(slower)" if rd.duration_delta_ms > 0 else "(faster)"
        lines.append(
            f"  Duration: {rd.old_duration_ms:.0f}ms → {rd.new_duration_ms:.0f}ms "
            f"({direction} {abs(rd.duration_delta_pct):.1f}%)"
        )
    else:
        lines.append(f"  Duration: {rd.old_duration_ms:.0f}ms → {rd.new_duration_ms:.0f}ms")

    lines.append("")

    # Events diff
    lines.append("-" * 40)
    lines.append("EVENTS")
    lines.append("-" * 40)

    if report.event_count_changed:
        lines.append(f"  Count: {report.event_count_a} → {report.event_count_b}")
    else:
        lines.append(f"  Count: {report.event_count_a} (unchanged)")

    if report.event_diffs:
        lines.append("")
        lines.append("  Changed events:")
        for diff in report.event_diffs:
            icon = "[FAIL]" if diff.is_critical else "[WARN]"
            lines.append(f"    {icon} #{diff.event_index} [{diff.event_type}]: {diff.summary}")

    if report.extra_events_a:
        lines.append("")
        lines.append(f"  Events only in baseline: {report.extra_events_a}")

    if report.extra_events_b:
        lines.append("")
        lines.append(f"  Events only in comparison: {report.extra_events_b}")

    lines.append("")

    # Summary
    lines.append("-" * 40)
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total duration change: {report.total_duration_delta_ms:+.0f}ms")
    lines.append(f"  Critical differences:  {report.critical_diffs}")
    lines.append("")

    return "\n".join(lines)
