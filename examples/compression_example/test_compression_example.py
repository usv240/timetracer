"""
Tests for the compression example.

Run with: pytest test_compression_example.py -v
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

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


@pytest.fixture
def sample_cassette() -> Cassette:
    """Create a sample cassette."""
    return Cassette(
        schema_version="1.0",
        session=SessionMeta(
            id="test-session",
            recorded_at="2026-01-22T12:00:00Z",
            service="test-service",
            env="test",
            framework="fastapi",
            timetracer_version="1.4.0",
            python_version="3.12.0",
            git_sha=None,
        ),
        request=RequestSnapshot(
            method="GET",
            path="/api/test",
            route_template="/api/test",
            headers={"content-type": "application/json"},
            query={},
            body=None,
            client_ip="127.0.0.1",
            user_agent="test",
        ),
        response=ResponseSnapshot(
            status=200,
            headers={"content-type": "application/json"},
            body=BodySnapshot(
                captured=True,
                encoding="utf-8",
                data={"message": "Hello, World!" * 50},
                truncated=False,
                size_bytes=750,
                hash="test",
            ),
            duration_ms=50.0,
        ),
        events=[],
        policies=AppliedPolicies(
            redaction_mode="default",
            redaction_rules=[],
            max_body_kb=64,
            store_request_body="on_error",
            store_response_body="on_error",
            sample_rate=1.0,
            errors_only=False,
        ),
        stats=CaptureStats(
            event_counts={},
            total_events=0,
            total_duration_ms=0.0,
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


def test_gzip_compression_works(tmp_path: Path, sample_cassette: Cassette):
    """Test that gzip compression creates smaller files."""
    mock_session = MockSession(sample_cassette)

    # Write uncompressed
    config_none = TraceConfig(
        cassette_dir=str(tmp_path / "none"),
        compression=CompressionType.NONE,
    )
    path_none = write_cassette(mock_session, config_none)
    size_none = Path(path_none).stat().st_size

    # Write compressed
    config_gzip = TraceConfig(
        cassette_dir=str(tmp_path / "gzip"),
        compression=CompressionType.GZIP,
    )
    path_gzip = write_cassette(mock_session, config_gzip)
    size_gzip = Path(path_gzip).stat().st_size

    # Verify gzip is smaller
    assert size_gzip < size_none
    assert path_gzip.endswith(".json.gz")


def test_gzip_roundtrip(tmp_path: Path, sample_cassette: Cassette):
    """Test that data survives compression round-trip."""
    mock_session = MockSession(sample_cassette)

    config = TraceConfig(
        cassette_dir=str(tmp_path),
        compression=CompressionType.GZIP,
    )
    path = write_cassette(mock_session, config)
    loaded = read_cassette(path)

    assert loaded.session.id == sample_cassette.session.id
    assert loaded.request.method == sample_cassette.request.method
    assert loaded.response.status == sample_cassette.response.status


def test_config_from_env(monkeypatch):
    """Test that compression can be set via environment variable."""
    monkeypatch.setenv("TIMETRACER_COMPRESSION", "gzip")
    config = TraceConfig.from_env()
    assert config.compression == CompressionType.GZIP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
