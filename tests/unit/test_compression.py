"""
Tests for cassette compression feature.

Tests gzip compression for cassettes, auto-detection on read,
and configuration via environment variables.
"""

import gzip
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from timetracer.cassette.io import read_cassette, write_cassette
from timetracer.config import TraceConfig
from timetracer.constants import CompressionType
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
    """Create a sample cassette for testing."""
    return Cassette(
        schema_version="1.0",
        session=SessionMeta(
            id="test-session-123",
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
            user_agent="test-agent",
        ),
        response=ResponseSnapshot(
            status=200,
            headers={"content-type": "application/json"},
            body=BodySnapshot(
                captured=True,
                encoding="utf-8",
                data={"message": "Hello, World!" * 100},  # Some content to compress
                truncated=False,
                size_bytes=1500,
                hash="abc123",
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


@pytest.fixture
def mock_session(sample_cassette: Cassette) -> MagicMock:
    """Create a mock trace session that returns the sample cassette."""
    session = MagicMock()
    session._finalized = True
    session.session_id = "test-session-123"
    session.to_cassette.return_value = sample_cassette
    return session


class TestCompressionConfig:
    """Tests for compression configuration."""

    def test_default_compression_is_none(self):
        """Default compression should be NONE."""
        config = TraceConfig()
        assert config.compression == CompressionType.NONE

    def test_compression_from_string(self):
        """Compression should be parsed from string value."""
        config = TraceConfig(compression="gzip")
        assert config.compression == CompressionType.GZIP

    def test_compression_case_insensitive(self):
        """Compression string parsing should be case-insensitive."""
        config = TraceConfig(compression="GZIP")
        assert config.compression == CompressionType.GZIP

    def test_invalid_compression_raises_error(self):
        """Invalid compression value should raise ConfigurationError."""
        from timetracer.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError, match="Invalid compression"):
            TraceConfig(compression="invalid")

    def test_compression_from_env(self):
        """Compression should be loaded from environment variable."""
        with patch.dict(os.environ, {"TIMETRACER_COMPRESSION": "gzip"}):
            config = TraceConfig.from_env()
            assert config.compression == CompressionType.GZIP

    def test_compression_env_override(self):
        """Environment variable should override code config."""
        base_config = TraceConfig(compression=CompressionType.NONE)
        with patch.dict(os.environ, {"TIMETRACER_COMPRESSION": "gzip"}):
            config = base_config.with_env_overrides()
            assert config.compression == CompressionType.GZIP


class TestWriteCassetteCompression:
    """Tests for writing compressed cassettes."""

    def test_write_uncompressed_cassette(
        self, tmp_path: Path, mock_session: MagicMock
    ):
        """Writing with compression=none should create .json file."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.NONE,
        )

        result_path = write_cassette(mock_session, config)

        assert result_path.endswith(".json")
        assert not result_path.endswith(".json.gz")
        assert Path(result_path).exists()

        # Verify it's valid JSON
        with open(result_path, "r") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0"

    def test_write_gzip_compressed_cassette(
        self, tmp_path: Path, mock_session: MagicMock
    ):
        """Writing with compression=gzip should create .json.gz file."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.GZIP,
        )

        result_path = write_cassette(mock_session, config)

        assert result_path.endswith(".json.gz")
        assert Path(result_path).exists()

        # Verify it's valid gzip JSON
        with gzip.open(result_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0"

    def test_gzip_compression_reduces_size(
        self, tmp_path: Path, mock_session: MagicMock
    ):
        """Gzip compression should produce smaller files."""
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

        # Compressed should be smaller
        assert size_gzip < size_none
        # Typically gzip achieves at least 50% compression on JSON
        assert size_gzip < size_none * 0.8


class TestReadCassetteCompression:
    """Tests for reading compressed cassettes."""

    def test_read_uncompressed_cassette(
        self, tmp_path: Path, mock_session: MagicMock
    ):
        """Should read uncompressed .json cassettes."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.NONE,
        )
        written_path = write_cassette(mock_session, config)

        cassette = read_cassette(written_path)

        assert cassette.schema_version == "1.0"
        assert cassette.session.id == "test-session-123"
        assert cassette.request.method == "GET"
        assert cassette.response.status == 200

    def test_read_gzip_compressed_cassette(
        self, tmp_path: Path, mock_session: MagicMock
    ):
        """Should read gzip compressed .json.gz cassettes."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.GZIP,
        )
        written_path = write_cassette(mock_session, config)

        cassette = read_cassette(written_path)

        assert cassette.schema_version == "1.0"
        assert cassette.session.id == "test-session-123"
        assert cassette.request.method == "GET"
        assert cassette.response.status == 200

    def test_auto_detect_gzip_by_extension(self, tmp_path: Path):
        """Should auto-detect gzip compression by .gz extension."""
        # Create a gzip file manually
        cassette_data = {
            "schema_version": "1.0",
            "session": {
                "id": "manual-test",
                "recorded_at": "2026-01-22T12:00:00Z",
                "service": "test",
                "env": "test",
                "framework": "fastapi",
                "timetracer_version": "1.4.0",
                "python_version": "3.12.0",
            },
            "request": {"method": "POST", "path": "/test"},
            "response": {"status": 201, "duration_ms": 25.0},
            "events": [],
            "policies": {
                "redaction": {"mode": "default", "rules": []},
                "capture": {
                    "max_body_kb": 64,
                    "store_request_body": "on_error",
                    "store_response_body": "on_error",
                },
                "sampling": {"rate": 1.0, "errors_only": False},
            },
            "stats": {
                "event_counts": {},
                "total_events": 0,
                "total_duration_ms": 0.0,
            },
        }

        gz_path = tmp_path / "manual.json.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            json.dump(cassette_data, f)

        cassette = read_cassette(str(gz_path))

        assert cassette.session.id == "manual-test"
        assert cassette.request.method == "POST"
        assert cassette.response.status == 201

    def test_read_missing_file_raises_error(self, tmp_path: Path):
        """Reading non-existent file should raise CassetteNotFoundError."""
        from timetracer.exceptions import CassetteNotFoundError

        with pytest.raises(CassetteNotFoundError):
            read_cassette(str(tmp_path / "does_not_exist.json"))

        with pytest.raises(CassetteNotFoundError):
            read_cassette(str(tmp_path / "does_not_exist.json.gz"))


class TestCompressionRoundTrip:
    """Tests for write-then-read round-trip with compression."""

    def test_roundtrip_uncompressed(
        self, tmp_path: Path, mock_session: MagicMock, sample_cassette: Cassette
    ):
        """Round-trip should preserve all data without compression."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.NONE,
        )

        written_path = write_cassette(mock_session, config)
        loaded = read_cassette(written_path)

        assert loaded.schema_version == sample_cassette.schema_version
        assert loaded.session.id == sample_cassette.session.id
        assert loaded.request.method == sample_cassette.request.method
        assert loaded.response.status == sample_cassette.response.status
        assert loaded.response.body.data == sample_cassette.response.body.data

    def test_roundtrip_gzip(
        self, tmp_path: Path, mock_session: MagicMock, sample_cassette: Cassette
    ):
        """Round-trip should preserve all data with gzip compression."""
        config = TraceConfig(
            cassette_dir=str(tmp_path),
            compression=CompressionType.GZIP,
        )

        written_path = write_cassette(mock_session, config)
        loaded = read_cassette(written_path)

        assert loaded.schema_version == sample_cassette.schema_version
        assert loaded.session.id == sample_cassette.session.id
        assert loaded.request.method == sample_cassette.request.method
        assert loaded.response.status == sample_cassette.response.status
        assert loaded.response.body.data == sample_cassette.response.body.data
