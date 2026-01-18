"""
Integration test for aiohttp plugin.

Tests the full record/replay flow with a real FastAPI app.
"""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from timetracer.config import TraceConfig, TraceMode
from timetracer.integrations.fastapi import TimeTraceMiddleware
from timetracer.plugins import enable_aiohttp, disable_aiohttp


def create_test_app(config: TraceConfig) -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.add_middleware(TimeTraceMiddleware, config=config)

    @app.get("/fetch")
    async def fetch():
        """Endpoint that makes an aiohttp call."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/get") as resp:
                data = await resp.json()
                return {"status": "ok", "origin": data.get("origin")}

    @app.post("/post-data")
    async def post_data():
        """Endpoint that makes an aiohttp POST call."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://httpbin.org/post",
                json={"test": "data"},
            ) as resp:
                data = await resp.json()
                return {"status": "ok", "json": data.get("json")}

    return app


@pytest.fixture
def temp_cassette_dir():
    """Create a temporary directory for cassettes."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_aiohttp_record_creates_cassette(temp_cassette_dir):
    """Test that aiohttp calls are recorded in cassettes."""
    config = TraceConfig(
        mode=TraceMode.RECORD,
        cassette_dir=temp_cassette_dir,
    )

    app = create_test_app(config)
    enable_aiohttp()

    try:
        client = TestClient(app)
        response = client.get("/fetch")
        assert response.status_code == 200
    finally:
        disable_aiohttp()

    # Check cassette was created
    cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
    assert len(cassettes) >= 1

    # Check cassette contains aiohttp event
    with open(cassettes[0]) as f:
        cassette = json.load(f)

    events = cassette.get("events", [])
    assert len(events) >= 1

    # Find the HTTP client event
    http_events = [e for e in events if e.get("type") == "http.client"]
    assert len(http_events) >= 1

    # Check the event has aiohttp signature
    event = http_events[0]
    sig = event.get("signature", {})
    assert sig.get("lib") == "aiohttp"
    assert sig.get("method") == "GET"
    assert "httpbin.org" in sig.get("url", "")


def test_aiohttp_post_recorded(temp_cassette_dir):
    """Test that aiohttp POST calls with body are recorded."""
    config = TraceConfig(
        mode=TraceMode.RECORD,
        cassette_dir=temp_cassette_dir,
    )

    app = create_test_app(config)
    enable_aiohttp()

    try:
        client = TestClient(app)
        response = client.post("/post-data")
        assert response.status_code == 200
    finally:
        disable_aiohttp()

    # Check cassette
    cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
    assert len(cassettes) >= 1

    with open(cassettes[0]) as f:
        cassette = json.load(f)

    events = cassette.get("events", [])
    http_events = [e for e in events if e.get("type") == "http.client"]
    assert len(http_events) >= 1

    event = http_events[0]
    sig = event.get("signature", {})
    assert sig.get("method") == "POST"
    assert sig.get("body_hash") is not None  # Body was hashed


def test_cassette_has_response_data(temp_cassette_dir):
    """Test that cassette contains response data."""
    config = TraceConfig(
        mode=TraceMode.RECORD,
        cassette_dir=temp_cassette_dir,
    )

    app = create_test_app(config)
    enable_aiohttp()

    try:
        client = TestClient(app)
        response = client.get("/fetch")
        assert response.status_code == 200
    finally:
        disable_aiohttp()

    cassettes = list(Path(temp_cassette_dir).glob("**/*.json"))
    with open(cassettes[0]) as f:
        cassette = json.load(f)

    events = cassette.get("events", [])
    http_events = [e for e in events if e.get("type") == "http.client"]
    event = http_events[0]

    result = event.get("result", {})
    assert result.get("status") == 200
    assert result.get("body") is not None
    assert result["body"].get("_captured") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
