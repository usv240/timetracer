"""Integration tests for Starlette."""

import tempfile
from pathlib import Path

import pytest

starlette = pytest.importorskip("starlette")
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from timetracer.cassette import read_cassette
from timetracer.config import TraceConfig
from timetracer.integrations.starlette import TimeTracerMiddleware, auto_setup


class TestStarletteIntegration:
    """Tests for Starlette middleware integration."""

    def test_record_simple_request(self):
        """Should record a simple GET request."""
        async def homepage(request):
            return JSONResponse({"message": "Hello, world!"})

        app = Starlette(debug=True, routes=[Route("/", homepage)])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200
            assert response.json() == {"message": "Hello, world!"}

            # Check cassette was created
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            # Verify cassette content
            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.method == "GET"
            assert cassette.request.path == "/"
            assert cassette.response.status == 200

    def test_record_post_request_with_body(self):
        """Should record POST request with JSON body."""
        async def create_user(request):
            body = await request.json()
            return JSONResponse({
                "id": 123,
                "username": body.get("username"),
                "created": True,
            })

        app = Starlette(debug=True, routes=[Route("/users", create_user, methods=["POST"])])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.post("/users", json={"username": "alice"})

            assert response.status_code == 200
            assert response.json()["username"] == "alice"

            # Check cassette
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.method == "POST"
            assert cassette.request.body is not None
            assert cassette.request.body.data == {"username": "alice"}

    def test_excluded_paths_not_recorded(self):
        """Health check endpoints should not be recorded."""
        async def health(request):
            return JSONResponse({"status": "ok"})

        async def api(request):
            return JSONResponse({"data": "value"})

        app = Starlette(
            debug=True,
            routes=[
                Route("/health", health),
                Route("/api", api),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(
                mode="record",
                cassette_dir=tmpdir,
                exclude_paths=["/health"],
            )
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)

            # Health should not be recorded
            client.get("/health")

            # API should be recorded
            client.get("/api")

            # Only one cassette should exist
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.path == "/api"

    def test_error_recording(self):
        """Should record error responses."""
        async def error_endpoint(request):
            return JSONResponse({"error": "Something went wrong"}, status_code=500)

        app = Starlette(debug=True, routes=[Route("/error", error_endpoint)])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.get("/error")

            assert response.status_code == 500

            # Check cassette was created
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            cassette = read_cassette(str(cassettes[0]))
            assert cassette.response.status == 500

    def test_errors_only_mode(self):
        """errors_only mode should only record failed requests."""
        async def success(request):
            return JSONResponse({"status": "ok"})

        async def failure(request):
            return JSONResponse({"error": "bad"}, status_code=400)

        app = Starlette(
            debug=True,
            routes=[
                Route("/success", success),
                Route("/failure", failure),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(
                mode="record",
                cassette_dir=tmpdir,
                errors_only=True,
            )
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)

            # Success should NOT be recorded
            client.get("/success")

            # Failure should be recorded
            client.get("/failure")

            # Only one cassette (the error)
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.path == "/failure"
            assert cassette.response.status == 400

    def test_auto_setup(self):
        """auto_setup should configure middleware correctly."""
        async def homepage(request):
            return JSONResponse({"message": "auto setup works"})

        app = Starlette(debug=True, routes=[Route("/", homepage)])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            auto_setup(app, config=config, plugins=[])

            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200

            # Cassette should be created
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1

    def test_replay_mode(self):
        """Replay mode should work with Starlette."""
        async def api_endpoint(request):
            return JSONResponse({"data": "from app"})

        Starlette(debug=True, routes=[Route("/api", api_endpoint)])  # noqa: F841

        with tempfile.TemporaryDirectory() as tmpdir:
            # First, record a cassette
            record_config = TraceConfig(mode="record", cassette_dir=tmpdir)
            record_app = Starlette(debug=True, routes=[Route("/api", api_endpoint)])
            record_app.add_middleware(TimeTracerMiddleware, config=record_config)

            record_client = TestClient(record_app)
            record_client.get("/api")

            # Get the cassette path
            cassettes = list(Path(tmpdir).rglob("*.json"))
            assert len(cassettes) == 1
            cassette_path = str(cassettes[0])

            # Now replay
            replay_config = TraceConfig(
                mode="replay",
                cassette_path=cassette_path,
            )
            replay_app = Starlette(debug=True, routes=[Route("/api", api_endpoint)])
            replay_app.add_middleware(TimeTracerMiddleware, config=replay_config)

            replay_client = TestClient(replay_app)
            response = replay_client.get("/api")

            # Should still work
            assert response.status_code == 200

    def test_path_parameters(self):
        """Should handle path parameters correctly."""
        async def get_user(request):
            user_id = request.path_params["user_id"]
            return JSONResponse({"id": user_id, "name": f"User {user_id}"})

        app = Starlette(
            debug=True,
            routes=[Route("/users/{user_id:int}", get_user)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.get("/users/42")

            assert response.status_code == 200
            assert response.json()["id"] == 42  #  Path parameter is parsed as int

            # Check cassette
            cassettes = list(Path(tmpdir).rglob("*.json"))
            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.path == "/users/42"

    def test_query_parameters(self):
        """Should capture query parameters."""
        async def search(request):
            query = request.query_params.get("q", "")
            return JSONResponse({"results": f"Results for: {query}"})

        app = Starlette(debug=True, routes=[Route("/search", search)])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.get("/search?q=starlette")

            assert response.status_code == 200

            # Check cassette
            cassettes = list(Path(tmpdir).rglob("*.json"))
            cassette = read_cassette(str(cassettes[0]))
            assert cassette.request.query == {"q": "starlette"}

    def test_headers_captured(self):
        """Should capture request and response headers."""
        async def echo_headers(request):
            return JSONResponse(
                {"user_agent": request.headers.get("user-agent")},
                headers={"X-Custom-Header": "test-value"},
            )

        app = Starlette(debug=True, routes=[Route("/", echo_headers)])

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(mode="record", cassette_dir=tmpdir)
            app.add_middleware(TimeTracerMiddleware, config=config)

            client = TestClient(app)
            response = client.get("/", headers={"User-Agent": "test-client"})

            assert response.status_code == 200
            assert response.headers["x-custom-header"] == "test-value"

            # Check cassette
            cassettes = list(Path(tmpdir).rglob("*.json"))
            cassette = read_cassette(str(cassettes[0]))

            # Request headers should be captured
            assert "user-agent" in cassette.request.headers

            # Response headers should be captured
            assert "x-custom-header" in cassette.response.headers
