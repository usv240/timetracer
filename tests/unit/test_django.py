"""
Unit tests for Django middleware.

Tests the Django integration without needing a full Django app.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestDjangoMiddlewareImport:
    """Test that Django middleware can be imported."""

    def test_import_middleware(self):
        """Test importing the middleware class."""
        from timetracer.integrations.django import TimeTracerMiddleware
        assert TimeTracerMiddleware is not None

    def test_import_auto_setup(self):
        """Test importing auto_setup function."""
        from timetracer.integrations.django import auto_setup
        assert callable(auto_setup)

    def test_import_alias(self):
        """Test importing DjangoMiddleware alias."""
        from timetracer.integrations.django import DjangoMiddleware
        assert DjangoMiddleware is not None


class TestDjangoConfigLoading:
    """Test configuration loading from Django settings."""

    def test_load_from_env_when_no_django_settings(self):
        """Test that config loads from env when no Django settings."""
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_get_response = MagicMock(return_value=MagicMock())
        middleware = TimeTracerMiddleware(mock_get_response)

        # Should have loaded default config
        assert middleware.config is not None
        assert middleware.config.mode == "off"  # Default mode

    def test_load_from_django_settings(self):
        """Test loading config from Django settings."""
        from timetracer.integrations.django import _get_django_settings_config

        # This test just verifies the function exists and can be called
        # Full Django settings testing requires a Django environment
        result = _get_django_settings_config()
        assert isinstance(result, dict)


class TestDjangoMiddlewareSync:
    """Test sync request handling."""

    def test_middleware_passes_through_when_disabled(self):
        """Test that middleware passes through when disabled."""
        from timetracer.config import TraceConfig
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_response = MagicMock()
        mock_get_response = MagicMock(return_value=mock_response)

        with patch.object(TimeTracerMiddleware, '_load_config') as mock_config:
            mock_config.return_value = TraceConfig(mode="off")
            middleware = TimeTracerMiddleware(mock_get_response)

            mock_request = MagicMock()
            mock_request.path = "/api/test"

            response = middleware(mock_request)

            mock_get_response.assert_called_once_with(mock_request)
            assert response == mock_response

    def test_middleware_skips_excluded_paths(self):
        """Test that excluded paths are skipped."""
        from timetracer.config import TraceConfig
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_response = MagicMock()
        mock_get_response = MagicMock(return_value=mock_response)

        with patch.object(TimeTracerMiddleware, '_load_config') as mock_config:
            mock_config.return_value = TraceConfig(
                mode="record",
                exclude_paths=["/health", "/metrics"],
            )
            middleware = TimeTracerMiddleware(mock_get_response)

            mock_request = MagicMock()
            mock_request.path = "/health"

            middleware(mock_request)

            # Should pass through without recording
            mock_get_response.assert_called_once_with(mock_request)


class TestDjangoRequestCapture:
    """Test request capture functionality."""

    def test_capture_request_method(self):
        """Test capturing request method."""
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_get_response = MagicMock()
        middleware = TimeTracerMiddleware(mock_get_response)

        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.path = "/api/users"
        mock_request.META = {
            "HTTP_CONTENT_TYPE": "application/json",
            "REMOTE_ADDR": "127.0.0.1",
        }
        mock_request.GET = {}
        mock_request.body = b'{"name": "test"}'
        mock_request.resolver_match = None

        snapshot = middleware._capture_request(mock_request)

        assert snapshot.method == "POST"
        assert snapshot.path == "/api/users"

    def test_capture_request_headers(self):
        """Test capturing and redacting headers."""
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_get_response = MagicMock()
        middleware = TimeTracerMiddleware(mock_get_response)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.path = "/api/test"
        mock_request.META = {
            "HTTP_CONTENT_TYPE": "application/json",
            "HTTP_X_REQUEST_ID": "req-123",
            "REMOTE_ADDR": "127.0.0.1",
        }
        mock_request.GET = {}
        mock_request.body = b""
        mock_request.resolver_match = None

        snapshot = middleware._capture_request(mock_request)

        # Headers should be captured (authorization is stripped by redact_headers)
        assert snapshot.headers.get("content-type") == "application/json"
        assert snapshot.headers.get("x-request-id") == "req-123"

    def test_capture_query_params(self):
        """Test capturing query parameters."""
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_get_response = MagicMock()
        middleware = TimeTracerMiddleware(mock_get_response)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.path = "/api/search"
        mock_request.META = {"REMOTE_ADDR": "127.0.0.1"}
        mock_request.GET = {"q": ["python"], "page": ["1"]}
        mock_request.body = b""
        mock_request.resolver_match = None

        snapshot = middleware._capture_request(mock_request)

        assert snapshot.query.get("q") == "python"
        assert snapshot.query.get("page") == "1"


class TestDjangoResponseCapture:
    """Test response capture functionality."""

    def test_capture_response_status(self):
        """Test capturing response status code."""
        from timetracer.config import TraceConfig
        from timetracer.integrations.django import TimeTracerMiddleware

        mock_get_response = MagicMock()

        with patch.object(TimeTracerMiddleware, '_load_config') as mock_config:
            mock_config.return_value = TraceConfig(mode="record")
            middleware = TimeTracerMiddleware(mock_get_response)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.items.return_value = [("Content-Type", "application/json")]
        mock_response.content = b'{"id": 1}'

        snapshot = middleware._build_response_snapshot(
            response=mock_response,
            duration_ms=50.0,
            is_error=False,
        )

        assert snapshot.status == 201
        assert snapshot.duration_ms == 50.0


class TestDjangoAutoSetup:
    """Test auto_setup function."""

    def test_auto_setup_enables_requests(self):
        """Test that auto_setup enables requests plugin by default."""
        from timetracer.integrations.django import auto_setup

        with patch("timetracer.plugins.enable_requests") as mock_enable:
            auto_setup()
            mock_enable.assert_called_once()

    def test_auto_setup_with_custom_plugins(self):
        """Test auto_setup with custom plugin list."""
        from timetracer.integrations.django import auto_setup

        with patch("timetracer.plugins.enable_httpx") as mock_httpx, \
             patch("timetracer.plugins.enable_aiohttp") as mock_aiohttp:
            auto_setup(plugins=["httpx", "aiohttp"])
            mock_httpx.assert_called_once()
            mock_aiohttp.assert_called_once()


class TestDjangoMiddlewareExports:
    """Test that Django middleware is exported correctly."""

    def test_export_from_integrations(self):
        """Test importing from integrations module."""
        from timetracer.integrations import DjangoMiddleware, django_auto_setup

        assert DjangoMiddleware is not None
        assert django_auto_setup is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
