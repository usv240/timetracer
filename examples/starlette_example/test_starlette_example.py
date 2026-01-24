"""
Tests for the Starlette example application.

Run:
    pytest test_starlette_example.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from timetracer.cassette import read_cassette
from timetracer.config import TraceConfig


# Import app from the example
from app import app


class TestStarletteExample:
    """Test the Starlette example application."""

    def test_homepage(self):
        """Homepage should return welcome message."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "/" in data["endpoints"]

    def test_github_user_endpoint(self):
        """Should fetch GitHub user info."""
        client = TestClient(app)
        response = client.get("/user/octocat")

        # Note: This will make a real API call unless in replay mode
        # For automated tests, you'd use a cassette
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == "octocat"

    def test_github_repos_endpoint(self):
        """Should fetch GitHub repos."""
        client = TestClient(app)
        response = client.get("/repos/octocat")

        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "total_repos" in data
        assert "top_repos" in data
        assert len(data["top_repos"]) > 0


    def test_user_not_found(self):
        """Should handle non-existent users."""
        client = TestClient(app)
        response = client.get("/user/this-user-definitely-does-not-exist-12345")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestWithRecordReplay:
    """Test record/replay functionality."""

    def test_record_mode(self):
        """Should record cassettes in record mode."""
        from app import app as starlette_app
        from timetracer.integrations.starlette import TimeTracerMiddleware

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fresh app with record config
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route

            async def homepage(request):
                return JSONResponse({"message": "test"})

            test_app = Starlette(debug=True, routes=[Route("/", homepage)])

            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            test_app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(test_app)
            response = client.get("/")

            assert response.status_code == 200

            # Check cassette was created
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            # Verify cassette content
            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.path == "/"
            assert cassette.response.status == 200

    def test_replay_mode(self):
        """Should replay from cassettes."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from timetracer.integrations.starlette import TimeTracerMiddleware

        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Record
            async def api_endpoint(request):
                return JSONResponse({"data": "original"})

            record_app = Starlette(
                debug=True, routes=[Route("/api", api_endpoint)]
            )
            record_config = TraceConfig(mode="record", cassette_dir=tmpdir)
            record_app.add_middleware(TimeTracerMiddleware, config=record_config)

            record_client = TestClient(record_app)
            record_client.get("/api")

            # Get cassette path
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1
            cassette_path = str(cassettes[0])

            # Step 2: Replay
            replay_app = Starlette(
                debug=True, routes=[Route("/api", api_endpoint)]
            )
            replay_config = TraceConfig(mode="replay", cassette_path=cassette_path)
            replay_app.add_middleware(TimeTracerMiddleware, config=replay_config)

            replay_client = TestClient(replay_app)
            response = replay_client.get("/api")

            assert response.status_code == 200
            assert response.json()["data"] == "original"


class TestWithHTTPX:
    """Test httpx plugin integration."""

    def test_httpx_calls_recorded(self):
        """httpx calls should be recorded as events."""
        import httpx
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from timetracer.integrations.starlette import auto_setup

        with tempfile.TemporaryDirectory() as tmpdir:

            async def external_call(request):
                async with httpx.AsyncClient() as client:
                    response = await client.get("https://httpbin.org/json")
                    return JSONResponse(response.json())

            test_app = Starlette(
                debug=True, routes=[Route("/external", external_call)]
            )

            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            auto_setup(test_app, config=config, plugins=["httpx"])

            client = TestClient(test_app)
            response = client.get("/external")

            assert response.status_code == 200

            # Check cassette
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            cassette = read_cassette(str(cassettes[0]))

            # Should have at least one http.client event
            assert len(cassette.events) >= 1
            http_events = [e for e in cassette.events if e.event_type.value == "http.client"]
            assert len(http_events) >= 1

            # Verify the httpx call was captured
            http_event = http_events[0]
            assert http_event.signature.method == "GET"
            assert "httpbin.org" in http_event.signature.url


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
