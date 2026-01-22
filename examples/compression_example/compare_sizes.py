"""
Script to compare cassette sizes with and without compression.

This demonstrates the storage savings from gzip compression.
"""

import gzip
import json
import os
import shutil
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from timetracer import CompressionType, TraceConfig
from timetracer.cassette.io import read_cassette, write_cassette
from timetracer.types import (
    AppliedPolicies,
    BodySnapshot,
    CaptureStats,
    Cassette,
    RequestSnapshot,
    ResponseSnapshot,
    SessionMeta,
)


def create_sample_cassette() -> Cassette:
    """Create a realistic sample cassette with substantial data."""
    # Simulate a large API response
    large_response_data = {
        "users": [
            {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "profile": {
                    "bio": f"This is a detailed biography for user {i}. " * 10,
                    "interests": ["coding", "reading", "hiking"],
                    "metadata": {"joined": "2026-01-01", "verified": True},
                },
            }
            for i in range(50)
        ],
        "pagination": {"page": 1, "per_page": 50, "total": 500},
    }

    return Cassette(
        schema_version="1.0",
        session=SessionMeta(
            id="compression-demo-session",
            recorded_at="2026-01-22T12:00:00Z",
            service="compression-demo",
            env="demo",
            framework="fastapi",
            timetracer_version="1.4.0",
            python_version="3.12.0",
            git_sha="abc123def",
        ),
        request=RequestSnapshot(
            method="GET",
            path="/api/users",
            route_template="/api/users",
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                "user-agent": "python-httpx/0.24.0",
            },
            query={"page": "1", "per_page": "50"},
            body=None,
            client_ip="127.0.0.1",
            user_agent="python-httpx/0.24.0",
        ),
        response=ResponseSnapshot(
            status=200,
            headers={
                "content-type": "application/json",
                "x-request-id": "req-12345",
            },
            body=BodySnapshot(
                captured=True,
                encoding="utf-8",
                data=large_response_data,
                truncated=False,
                size_bytes=len(json.dumps(large_response_data)),
                hash="sha256-example",
            ),
            duration_ms=125.5,
        ),
        events=[],
        policies=AppliedPolicies(
            redaction_mode="default",
            redaction_rules=[],
            max_body_kb=64,
            store_request_body="on_error",
            store_response_body="always",
            sample_rate=1.0,
            errors_only=False,
        ),
        stats=CaptureStats(
            event_counts={"http.client": 1},
            total_events=1,
            total_duration_ms=125.5,
        ),
    )


class MockSession:
    """Mock session for write_cassette."""

    def __init__(self, cassette: Cassette):
        self._cassette = cassette
        self._finalized = True
        self.session_id = cassette.session.id

    def to_cassette(self) -> Cassette:
        return self._cassette


def compare_sizes():
    """Compare cassette sizes with and without compression."""
    print("=" * 60)
    print("Cassette Compression Size Comparison")
    print("=" * 60)
    print()

    # Create temp directories
    tmp_dir = Path(__file__).parent / ".tmp_comparison"
    tmp_dir.mkdir(exist_ok=True)

    try:
        # Create sample cassette
        cassette = create_sample_cassette()
        mock_session = MockSession(cassette)

        # Write without compression
        config_none = TraceConfig(
            cassette_dir=str(tmp_dir / "uncompressed"),
            compression=CompressionType.NONE,
        )
        path_none = write_cassette(mock_session, config_none)
        size_none = Path(path_none).stat().st_size

        # Write with gzip compression
        config_gzip = TraceConfig(
            cassette_dir=str(tmp_dir / "compressed"),
            compression=CompressionType.GZIP,
        )
        path_gzip = write_cassette(mock_session, config_gzip)
        size_gzip = Path(path_gzip).stat().st_size

        # Calculate savings
        savings_bytes = size_none - size_gzip
        savings_pct = (savings_bytes / size_none) * 100

        # Display results
        print(f"Sample cassette with 50 user records:\n")
        print(f"  [JSON] Uncompressed (.json):  {size_none:>8,} bytes")
        print(f"  [GZIP] Compressed (.json.gz): {size_gzip:>8,} bytes")
        print()
        print(f"  SAVED: {savings_bytes:,} bytes ({savings_pct:.1f}%)")
        print()

        # Verify round-trip
        print("Verifying round-trip integrity...")
        loaded_none = read_cassette(path_none)
        loaded_gzip = read_cassette(path_gzip)

        assert loaded_none.session.id == cassette.session.id
        assert loaded_gzip.session.id == cassette.session.id
        assert loaded_none.response.body.data == cassette.response.body.data
        assert loaded_gzip.response.body.data == cassette.response.body.data

        print("  [OK] Both formats read successfully")
        print("  [OK] Data integrity verified")
        print()

        # Show file paths
        print("Created files:")
        print(f"  {path_none}")
        print(f"  {path_gzip}")
        print()

        # Scaling estimate
        print("Scaling estimate (100 cassettes):")
        print(f"  Uncompressed: {size_none * 100 / (1024*1024):.2f} MB")
        print(f"  Compressed:   {size_gzip * 100 / (1024*1024):.2f} MB")
        print()

    finally:
        # Cleanup
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            print("Cleaned up temporary files")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    compare_sizes()
