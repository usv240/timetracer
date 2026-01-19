"""
Tests demonstrating the Timetracer pytest plugin fixtures.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from app import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def temp_cassette_dir():
    """Temporary directory for cassettes."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestBasicEndpoints:
    """Test basic endpoints without cassettes."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestReplayFixture:
    """Demonstrate timetracer_replay fixture."""

    def test_replay_fixture_works(self, timetracer_replay, client, tmp_path):
        """Test that replay fixture is available."""
        # The fixture is a context manager factory
        assert callable(timetracer_replay)

    def test_replay_raises_for_missing(self, timetracer_replay, tmp_path):
        """Test that missing cassette raises error."""
        with pytest.raises(FileNotFoundError):
            with timetracer_replay(tmp_path / "nonexistent.json"):
                pass


class TestRecordFixture:
    """Demonstrate timetracer_record fixture."""

    def test_record_creates_session(self, timetracer_record, client):
        """Test recording a new session."""
        from timetracer.session import TraceSession

        with timetracer_record(use_tmp=True) as session:
            # Make a request - this would be recorded
            response = client.get("/")
            assert response.status_code == 200

        # Session was properly created
        assert isinstance(session, TraceSession)


class TestAutoFixture:
    """Demonstrate timetracer_auto fixture."""

    def test_auto_fixture_available(self, timetracer_auto):
        """Test that auto fixture is available."""
        assert callable(timetracer_auto)


class TestIntegrationWithHttpx:
    """Test actual HTTP call recording with httpx."""

    def test_httpx_call_captured(self, timetracer_record, client):
        """Test that httpx calls are captured during recording."""
        from timetracer.plugins import disable_httpx, enable_httpx

        enable_httpx()
        try:
            with timetracer_record(use_tmp=True):
                response = client.get("/fetch-data")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
        finally:
            disable_httpx()


class TestCassetteDirectory:
    """Test cassette directory fixture."""

    def test_cassette_dir_is_path(self, timetracer_cassette_dir):
        """Test that cassette_dir returns a Path."""
        assert isinstance(timetracer_cassette_dir, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
