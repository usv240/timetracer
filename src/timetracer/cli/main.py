"""
Timetracer CLI.

Provides commands for managing and inspecting cassettes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from timetracer import __version__


def main(args: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="timetracer",
        description="Time-travel debugging for FastAPI - manage and inspect cassettes",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"timetracer {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List recorded cassettes",
    )
    list_parser.add_argument(
        "--dir", "-d",
        default="./cassettes",
        help="Cassette directory (default: ./cassettes)",
    )
    list_parser.add_argument(
        "--last", "-n",
        type=int,
        default=10,
        help="Number of recent cassettes to show (default: 10)",
    )

    # Show command
    show_parser = subparsers.add_parser(
        "show",
        help="Show cassette details",
    )
    show_parser.add_argument(
        "cassette",
        help="Path to cassette file",
    )
    show_parser.add_argument(
        "--events", "-e",
        action="store_true",
        help="Show event details",
    )

    # Diff command
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two cassettes",
    )
    diff_parser.add_argument(
        "--a", "-a",
        required=True,
        dest="cassette_a",
        help="Path to baseline cassette",
    )
    diff_parser.add_argument(
        "--b", "-b",
        required=True,
        dest="cassette_b",
        help="Path to comparison cassette",
    )
    diff_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON",
    )
    diff_parser.add_argument(
        "--out", "-o",
        dest="output",
        help="Write report to file",
    )
    diff_parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=20.0,
        help="Duration change threshold percentage (default: 20)",
    )

    # Timeline command
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Generate HTML timeline visualization",
    )
    timeline_parser.add_argument(
        "cassette",
        help="Path to cassette file",
    )
    timeline_parser.add_argument(
        "--out", "-o",
        dest="output",
        help="Output HTML file (default: cassette name + .html)",
    )
    timeline_parser.add_argument(
        "--open",
        action="store_true",
        help="Open in browser after generating",
    )

    # S3 commands
    s3_parser = subparsers.add_parser(
        "s3",
        help="S3 storage operations",
    )
    s3_subparsers = s3_parser.add_subparsers(dest="s3_command", help="S3 commands")

    # S3 upload
    s3_upload = s3_subparsers.add_parser("upload", help="Upload cassettes to S3")
    s3_upload.add_argument("path", help="Local cassette file or directory")
    s3_upload.add_argument("--bucket", "-b", help="S3 bucket (or TIMETRACER_S3_BUCKET)")
    s3_upload.add_argument("--prefix", "-p", default="cassettes", help="S3 prefix")

    # S3 download
    s3_download = s3_subparsers.add_parser("download", help="Download cassette from S3")
    s3_download.add_argument("key", help="S3 key to download")
    s3_download.add_argument("--out", "-o", help="Local output path")
    s3_download.add_argument("--bucket", "-b", help="S3 bucket")
    s3_download.add_argument("--prefix", "-p", default="cassettes", help="S3 prefix")

    # S3 list
    s3_list = s3_subparsers.add_parser("list", help="List cassettes in S3")
    s3_list.add_argument("--bucket", "-b", help="S3 bucket")
    s3_list.add_argument("--prefix", "-p", default="cassettes", help="S3 prefix")
    s3_list.add_argument("--limit", "-n", type=int, default=20, help="Max results")

    # S3 sync
    s3_sync = s3_subparsers.add_parser("sync", help="Sync cassettes with S3")
    s3_sync.add_argument("direction", choices=["up", "down"], help="Sync direction")
    s3_sync.add_argument("--dir", "-d", default="./cassettes", help="Local directory")
    s3_sync.add_argument("--bucket", "-b", help="S3 bucket")
    s3_sync.add_argument("--prefix", "-p", default="cassettes", help="S3 prefix")

    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search cassettes by endpoint, status, etc.",
    )
    search_parser.add_argument(
        "--dir", "-d",
        default="./cassettes",
        help="Cassette directory",
    )
    search_parser.add_argument(
        "--method", "-m",
        help="Filter by HTTP method (GET, POST, etc.)",
    )
    search_parser.add_argument(
        "--endpoint", "-e",
        help="Filter by endpoint path (partial match)",
    )
    search_parser.add_argument(
        "--status",
        type=int,
        help="Filter by exact status code",
    )
    search_parser.add_argument(
        "--errors",
        action="store_true",
        help="Only show error responses (4xx, 5xx)",
    )
    search_parser.add_argument(
        "--service", "-s",
        help="Filter by service name",
    )
    search_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=20,
        help="Maximum results (default: 20)",
    )
    search_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Index command
    index_parser = subparsers.add_parser(
        "index",
        help="Build cassette index for fast searching",
    )
    index_parser.add_argument(
        "--dir", "-d",
        default="./cassettes",
        help="Cassette directory",
    )
    index_parser.add_argument(
        "--out", "-o",
        help="Output index file (default: <dir>/index.json)",
    )

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Generate HTML dashboard to browse cassettes",
    )
    dashboard_parser.add_argument(
        "--dir", "-d",
        default="./cassettes",
        help="Cassette directory (default: ./cassettes)",
    )
    dashboard_parser.add_argument(
        "--out", "-o",
        dest="output",
        help="Output HTML file (default: dashboard.html)",
    )
    dashboard_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=500,
        help="Maximum cassettes to include (default: 500)",
    )
    dashboard_parser.add_argument(
        "--open",
        action="store_true",
        help="Open in browser after generating",
    )

    # Serve command (live dashboard)
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start live dashboard server with replay capability",
    )
    serve_parser.add_argument(
        "--dir", "-d",
        default="./cassettes",
        help="Cassette directory (default: ./cassettes)",
    )
    serve_parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="Server port (default: 8765)",
    )
    serve_parser.add_argument(
        "--open",
        action="store_true",
        help="Open in browser after starting",
    )

    parsed = parser.parse_args(args)

    if parsed.command == "list":
        return _cmd_list(parsed.dir, parsed.last)
    elif parsed.command == "show":
        return _cmd_show(parsed.cassette, parsed.events)
    elif parsed.command == "diff":
        return _cmd_diff(
            parsed.cassette_a,
            parsed.cassette_b,
            parsed.json,
            parsed.output,
            parsed.threshold,
        )
    elif parsed.command == "timeline":
        return _cmd_timeline(
            parsed.cassette,
            parsed.output,
            parsed.open,
        )
    elif parsed.command == "s3":
        return _cmd_s3(parsed)
    elif parsed.command == "search":
        return _cmd_search(parsed)
    elif parsed.command == "index":
        return _cmd_index(parsed)
    elif parsed.command == "dashboard":
        return _cmd_dashboard(parsed)
    elif parsed.command == "serve":
        return _cmd_serve(parsed)
    else:
        parser.print_help()
        return 0


def _cmd_list(directory: str, limit: int) -> int:
    """List cassettes in directory."""
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Directory not found: {directory}", file=sys.stderr)
        return 1

    # Find all cassette files
    cassettes: list[tuple[Path, float]] = []

    for json_file in dir_path.rglob("*.json"):
        try:
            mtime = json_file.stat().st_mtime
            cassettes.append((json_file, mtime))
        except OSError:
            continue

    if not cassettes:
        print(f"No cassettes found in {directory}")
        return 0

    # Sort by modification time (newest first)
    cassettes.sort(key=lambda x: x[1], reverse=True)

    # Limit results
    cassettes = cassettes[:limit]

    print(f"\nRecent cassettes in {directory}:\n")
    print(f"{'#':<4} {'Filename':<50} {'Size':>10}")
    print("-" * 70)

    for i, (path, _) in enumerate(cassettes, 1):
        relative = path.relative_to(dir_path)
        size = path.stat().st_size
        size_str = _format_size(size)
        print(f"{i:<4} {str(relative):<50} {size_str:>10}")

    print(f"\nShowing {len(cassettes)} of {sum(1 for _ in dir_path.rglob('*.json'))} total cassettes")

    return 0


def _cmd_show(cassette_path: str, show_events: bool) -> int:
    """Show cassette details."""
    from timetracer.cassette import read_cassette
    from timetracer.exceptions import CassetteNotFoundError, CassetteSchemaError

    try:
        cassette = read_cassette(cassette_path)
    except CassetteNotFoundError:
        print(f"Cassette not found: {cassette_path}", file=sys.stderr)
        return 1
    except CassetteSchemaError as e:
        print(f"Schema error: {e}", file=sys.stderr)
        return 1

    # Header
    print(f"\nCassette: {cassette_path}\n")
    print(f"Schema Version: {cassette.schema_version}")

    # Session info
    session = cassette.session
    print("\nSession:")
    print(f"  ID:          {session.id}")
    print(f"  Recorded:    {session.recorded_at}")
    print(f"  Service:     {session.service}")
    print(f"  Environment: {session.env}")

    # Request
    req = cassette.request
    print("\nRequest:")
    print(f"  {req.method} {req.path}")
    if req.route_template and req.route_template != req.path:
        print(f"  Route: {req.route_template}")
    if req.query:
        print(f"  Query: {req.query}")

    # Response
    res = cassette.response
    status_icon = "[OK]" if res.status < 400 else "[WARN]"
    print("\nResponse:")
    print(f"  {status_icon} Status: {res.status}")
    print(f"  Duration: {res.duration_ms:.2f}ms")

    # Events summary
    print(f"\nEvents: {len(cassette.events)} total")

    if cassette.stats.event_counts:
        for event_type, count in cassette.stats.event_counts.items():
            print(f"  {event_type}: {count}")

    # Event details (optional)
    if show_events and cassette.events:
        print("\nEvent Details:")
        for event in cassette.events:
            sig = event.signature
            print(f"\n  #{event.eid} [{event.event_type.value}]")
            print(f"    {sig.method} {sig.url}")
            print(f"    Offset: +{event.start_offset_ms:.1f}ms, Duration: {event.duration_ms:.1f}ms")
            if event.result.status:
                result_icon = "[OK]" if event.result.status < 400 else "[WARN]"
                print(f"    {result_icon} Response: {event.result.status}")

    print()  # Final newline
    return 0


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def _cmd_diff(
    cassette_a: str,
    cassette_b: str,
    as_json: bool,
    output: str | None,
    threshold: float,
) -> int:
    """Compare two cassettes and show differences."""
    import json

    from timetracer.diff import diff_cassettes, format_diff_report
    from timetracer.exceptions import CassetteNotFoundError, CassetteSchemaError

    try:
        report = diff_cassettes(cassette_a, cassette_b, duration_threshold_pct=threshold)
    except CassetteNotFoundError as e:
        print(f"Cassette not found: {e.path}", file=sys.stderr)
        return 1
    except CassetteSchemaError as e:
        print(f"Schema error: {e}", file=sys.stderr)
        return 1

    # Format output
    if as_json:
        output_text = json.dumps(report.to_dict(), indent=2)
    else:
        output_text = format_diff_report(report)

    # Write to file or stdout
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Report written to: {output}")
    else:
        print(output_text)

    # Return code based on result
    if report.is_regression:
        return 2  # Regression detected
    elif report.has_differences:
        return 1  # Differences found
    else:
        return 0  # No differences


def _cmd_timeline(
    cassette_path: str,
    output: str | None,
    open_browser: bool,
) -> int:
    """Generate HTML timeline visualization."""
    from timetracer.exceptions import CassetteNotFoundError, CassetteSchemaError
    from timetracer.timeline import generate_timeline, render_timeline_html

    try:
        timeline_data = generate_timeline(cassette_path)
    except CassetteNotFoundError:
        print(f"Cassette not found: {cassette_path}", file=sys.stderr)
        return 1
    except CassetteSchemaError as e:
        print(f"Schema error: {e}", file=sys.stderr)
        return 1

    # Generate HTML
    html_content = render_timeline_html(timeline_data)

    # Determine output path
    if output:
        output_path = output
    else:
        # Default: same name as cassette but .html
        output_path = cassette_path.rsplit(".", 1)[0] + ".html"

    # Write HTML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Timeline generated: {output_path}")
    print(f"   Request: {timeline_data.method} {timeline_data.path}")
    print(f"   Duration: {timeline_data.total_duration_ms:.1f}ms")
    print(f"   Events: {timeline_data.event_count}")

    # Open in browser if requested
    if open_browser:
        import webbrowser
        webbrowser.open(f"file://{Path(output_path).absolute()}")
        print("   Opened in browser")

    return 0


def _cmd_s3(parsed) -> int:
    """Handle S3 commands."""
    import os

    try:
        from timetracer.storage.s3 import S3Config, S3Store
    except ImportError:
        print("boto3 is required for S3 storage. Install with: pip install timetracer[s3]", file=sys.stderr)
        return 1

    # Get bucket from args or env
    bucket = getattr(parsed, 'bucket', None) or os.environ.get("TIMETRACER_S3_BUCKET")
    if not bucket:
        print("S3 bucket required. Set --bucket or TIMETRACER_S3_BUCKET", file=sys.stderr)
        return 1

    prefix = getattr(parsed, 'prefix', 'cassettes')

    config = S3Config(bucket=bucket, prefix=prefix)
    store = S3Store(config)

    cmd = parsed.s3_command

    if cmd == "upload":
        path = Path(parsed.path)
        if path.is_file():
            key = store.upload(str(path))
            print(f"Uploaded: s3://{bucket}/{key}")
        elif path.is_dir():
            keys = store.sync_upload(str(path))
            print(f"Uploaded {len(keys)} cassettes to s3://{bucket}/{prefix}/")
        else:
            print(f"Path not found: {path}", file=sys.stderr)
            return 1

    elif cmd == "download":
        out = parsed.out or f"./{parsed.key}"
        local = store.download(parsed.key, out)
        print(f"Downloaded: {local}")

    elif cmd == "list":
        limit = parsed.limit
        print(f"\nCassettes in s3://{bucket}/{prefix}/\n")
        count = 0
        for key in store.list(limit=limit):
            print(f"  {key}")
            count += 1
        print(f"\nShowing {count} cassettes")

    elif cmd == "sync":
        local_dir = parsed.dir
        if parsed.direction == "up":
            keys = store.sync_upload(local_dir)
            print(f"Synced {len(keys)} cassettes to s3://{bucket}/{prefix}/")
        else:
            paths = store.sync_download(local_dir)
            print(f"Downloaded {len(paths)} cassettes to {local_dir}")

    else:
        print("Unknown S3 command. Use: upload, download, list, sync", file=sys.stderr)
        return 1

    return 0


def _cmd_search(parsed) -> int:
    """Search cassettes."""
    import json as json_module

    from timetracer.catalog import search_cassettes

    results = search_cassettes(
        cassette_dir=parsed.dir,
        method=parsed.method,
        endpoint=parsed.endpoint,
        status_min=parsed.status,
        status_max=parsed.status,
        errors_only=parsed.errors,
        service=parsed.service,
        limit=parsed.limit,
    )

    if parsed.json:
        output = [r.to_dict() for r in results]
        print(json_module.dumps(output, indent=2))
    else:
        if not results:
            print("No cassettes found matching criteria.")
            return 0

        print(f"\nFound {len(results)} cassettes:\n")
        print(f"{'#':<4} {'Method':<8} {'Endpoint':<30} {'Status':<8} {'Duration':<10}")
        print("-" * 70)

        for i, entry in enumerate(results, 1):
            status_icon = "[OK]" if entry.status < 400 else "[ERR]"
            print(
                f"{i:<4} {entry.method:<8} {entry.endpoint[:28]:<30} "
                f"{status_icon}{entry.status:<6} {entry.duration_ms:.0f}ms"
            )

        print(f"\nShowing {len(results)} results")

    return 0


def _cmd_index(parsed) -> int:
    """Build cassette index."""
    from timetracer.catalog import build_index, save_index

    print(f"Building index for {parsed.dir}...")

    index = build_index(parsed.dir)

    output_path = parsed.out or f"{parsed.dir}/index.json"
    save_index(index, output_path)

    print(f"Indexed {index.total_count} cassettes")
    print(f"   Output: {output_path}")

    return 0


def _cmd_dashboard(parsed) -> int:
    """Generate HTML dashboard for browsing cassettes."""
    from pathlib import Path

    from timetracer.dashboard import generate_dashboard, render_dashboard_html

    print(f"Generating dashboard for {parsed.dir}...")

    # Generate dashboard data
    dashboard_data = generate_dashboard(parsed.dir, limit=parsed.limit)

    if dashboard_data.total_count == 0:
        print(f"No cassettes found in {parsed.dir}")
        return 1

    # Render HTML
    html_content = render_dashboard_html(dashboard_data)

    # Determine output path
    output_path = parsed.output or "dashboard.html"

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard generated: {output_path}")
    print(f"   Cassettes: {dashboard_data.total_count}")
    print(f"   Success: {dashboard_data.success_count}")
    print(f"   Errors: {dashboard_data.error_count}")

    # Open in browser if requested
    if parsed.open:
        import webbrowser
        webbrowser.open(f"file://{Path(output_path).absolute()}")
        print("   Opened in browser")

    return 0


def _cmd_serve(parsed) -> int:
    """Start live dashboard server with replay capability."""
    import threading
    import webbrowser

    from timetracer.dashboard.server import start_server

    port = parsed.port
    url = f"http://localhost:{port}"

    # Open browser in a separate thread after a short delay
    if parsed.open:
        def open_browser():
            import time
            time.sleep(1)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    # Start server (blocks)
    start_server(parsed.dir, port)

    return 0


if __name__ == "__main__":
    sys.exit(main())




