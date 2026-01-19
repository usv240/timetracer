"""
Integration tests for FastAPI + aiohttp example.

Tests the full record/replay cycle with aiohttp.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from timetracer.config import TraceConfig, TraceMode
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import disable_aiohttp, enable_aiohttp


# Import the endpoints from app.py (we'll recreate them for testing)
def create_test_app(config: TraceConfig):
    """Create a test app with the given config."""
    import aiohttp
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(TimeTracerMiddleware, config=config)

    @app.get("/")
    async def root():
        return {"status": "ok", "client": "aiohttp"}

    @app.get("/fetch-data")
    async def fetch_data():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/json") as resp:
                data = await resp.json()
        return {"status": "success", "data": data}

    @app.post("/submit")
    async def submit_data():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://httpbin.org/post",
                json={"action": "submit", "value": 42},
            ) as resp:
                data = await resp.json()
        return {"status": "submitted", "response": data}

    @app.post("/multi-call")
    async def multi_call():
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/get") as resp1:
                get_data = await resp1.json()
            async with session.post(
                "https://httpbin.org/post",
                json={"from_get": get_data.get("origin")},
            ) as resp2:
                post_data = await resp2.json()
        return {"get_result": get_data, "post_result": post_data}

    @app.get("/with-params")
    async def with_params():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://httpbin.org/get",
                params={"page": 1, "limit": 10},
            ) as resp:
                data = await resp.json()
        return {"result": data}

    return app


@pytest.fixture
def temp_cassette_dir():
    """Create a temporary directory for cassettes."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestAiohttpRecording:
    """Test recording aiohttp calls."""

    def test_simple_get_recorded(self, temp_cassette_dir):
        """Test that simple GET with aiohttp is recorded."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        try:
            client = TestClient(app)
            response = client.get("/fetch-data")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
        finally:
            disable_aiohttp()

        # Verify cassette was created
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        assert len(cassettes) >= 1

        # Verify cassette has aiohttp event
        with open(cassettes[0]) as f:
            cassette = json.load(f)

        events = cassette.get("events", [])
        http_events = [e for e in events if e.get("type") == "http.client"]
        assert len(http_events) >= 1

        # Check it's aiohttp
        sig = http_events[0].get("signature", {})
        assert sig.get("lib") == "aiohttp"
        assert sig.get("method") == "GET"

    def test_post_with_body_recorded(self, temp_cassette_dir):
        """Test that POST with JSON body is recorded."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        try:
            client = TestClient(app)
            response = client.post("/submit")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "submitted"
        finally:
            disable_aiohttp()

        # Verify cassette
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        with open(cassettes[0]) as f:
            cassette = json.load(f)

        events = cassette.get("events", [])
        http_events = [e for e in events if e.get("type") == "http.client"]

        event = http_events[0]
        sig = event.get("signature", {})
        assert sig.get("method") == "POST"
        assert sig.get("body_hash") is not None  # Body was captured

    def test_multiple_calls_recorded(self, temp_cassette_dir):
        """Test that multiple aiohttp calls are all recorded."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        try:
            client = TestClient(app)
            response = client.post("/multi-call")
            assert response.status_code == 200
            data = response.json()
            assert "get_result" in data
            assert "post_result" in data
        finally:
            disable_aiohttp()

        # Verify cassette has 2 events
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        with open(cassettes[0]) as f:
            cassette = json.load(f)

        events = cassette.get("events", [])
        http_events = [e for e in events if e.get("type") == "http.client"]
        assert len(http_events) == 2  # GET + POST

    def test_query_params_recorded(self, temp_cassette_dir):
        """Test that query parameters are recorded."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        try:
            client = TestClient(app)
            response = client.get("/with-params")
            assert response.status_code == 200
        finally:
            disable_aiohttp()

        # Verify query params in cassette
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        with open(cassettes[0]) as f:
            cassette = json.load(f)

        events = cassette.get("events", [])
        http_events = [e for e in events if e.get("type") == "http.client"]

        sig = http_events[0].get("signature", {})
        query = sig.get("query", {})
        assert query.get("page") == 1
        assert query.get("limit") == 10


class TestAiohttpReplay:
    """Test replaying aiohttp calls from cassettes."""

    def test_replay_returns_recorded_data(self, temp_cassette_dir):
        """Test that replay returns the recorded response."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        # Record first
        try:
            client = TestClient(app)
            response = client.get("/fetch-data")
            assert response.status_code == 200
            recorded_data = response.json()
        finally:
            disable_aiohttp()

        # Get the cassette path
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        cassette_path = str(cassettes[0])

        # Now replay
        replay_config = TraceConfig(
            mode=TraceMode.REPLAY,
            cassette_path=cassette_path,
        )
        replay_app = create_test_app(replay_config)
        enable_aiohttp()

        try:
            replay_client = TestClient(replay_app)
            replay_response = replay_client.get("/fetch-data")
            assert replay_response.status_code == 200
            replay_data = replay_response.json()

            # Data should match (response from mocked aiohttp)
            assert replay_data["status"] == recorded_data["status"]
        finally:
            disable_aiohttp()


class TestAiohttpEdgeCases:
    """Test edge cases and error handling."""

    def test_no_external_calls(self, temp_cassette_dir):
        """Test endpoint that doesn't make external calls."""
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=temp_cassette_dir,
        )
        app = create_test_app(config)
        enable_aiohttp()

        try:
            client = TestClient(app)
            response = client.get("/")
            assert response.status_code == 200
            assert response.json()["client"] == "aiohttp"
        finally:
            disable_aiohttp()

        # Cassette should have no HTTP events
        cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
        with open(cassettes[0]) as f:
            cassette = json.load(f)

        events = cassette.get("events", [])
        http_events = [e for e in events if e.get("type") == "http.client"]
        assert len(http_events) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
