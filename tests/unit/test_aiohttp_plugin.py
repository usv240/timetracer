"""
Unit tests for aiohttp plugin.
"""

import pytest


class TestEnableDisable:
    """Test enable/disable functions."""

    def test_enable_aiohttp(self):
        """Test enabling aiohttp plugin."""
        import aiohttp

        from timetracer.plugins import disable_aiohttp, enable_aiohttp

        original = aiohttp.ClientSession._request

        enable_aiohttp()
        assert aiohttp.ClientSession._request is not original

        disable_aiohttp()
        assert aiohttp.ClientSession._request is original

    def test_enable_twice_is_safe(self):
        """Test that enabling twice doesn't break anything."""
        from timetracer.plugins import disable_aiohttp, enable_aiohttp

        enable_aiohttp()
        enable_aiohttp()  # Should not raise
        disable_aiohttp()

    def test_disable_without_enable_is_safe(self):
        """Test that disabling without enabling is safe."""
        from timetracer.plugins import disable_aiohttp

        disable_aiohttp()  # Should not raise


class TestSignatureCreation:
    """Test signature creation from requests."""

    def test_basic_signature(self):
        """Test basic signature creation."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="GET",
            url="https://api.example.com/users",
            kwargs={},
        )

        assert sig.lib == "aiohttp"
        assert sig.method == "GET"
        assert sig.url == "https://api.example.com/users"
        assert sig.query == {}
        assert sig.body_hash is None

    def test_signature_with_query_params(self):
        """Test signature with query params in URL."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="GET",
            url="https://api.example.com/users?page=1&limit=10",
            kwargs={},
        )

        assert sig.url == "https://api.example.com/users"
        assert sig.query == {"page": "1", "limit": "10"}

    def test_signature_with_params_kwarg(self):
        """Test signature with params in kwargs."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="GET",
            url="https://api.example.com/users",
            kwargs={"params": {"page": 1, "limit": 10}},
        )

        assert sig.query == {"page": 1, "limit": 10}

    def test_signature_with_json_body(self):
        """Test signature with JSON body."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="POST",
            url="https://api.example.com/users",
            kwargs={"json": {"name": "test", "email": "test@example.com"}},
        )

        assert sig.body_hash is not None

    def test_signature_with_data_body(self):
        """Test signature with data body."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="POST",
            url="https://api.example.com/users",
            kwargs={"data": b"raw bytes"},
        )

        assert sig.body_hash is not None

    def test_method_normalized_to_uppercase(self):
        """Test that method is normalized to uppercase."""
        from timetracer.plugins.aiohttp_plugin import _make_signature

        sig = _make_signature(
            method="post",
            url="https://api.example.com/users",
            kwargs={},
        )

        assert sig.method == "POST"


class TestMockResponse:
    """Test mock response object."""

    @pytest.mark.asyncio
    async def test_read(self):
        """Test reading response body."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={},
            content=b'{"message": "hello"}',
        )

        body = await response.read()
        assert body == b'{"message": "hello"}'

    @pytest.mark.asyncio
    async def test_text(self):
        """Test reading response as text."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={},
            content=b"Hello World",
        )

        text = await response.text()
        assert text == "Hello World"

    @pytest.mark.asyncio
    async def test_json(self):
        """Test reading response as JSON."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={},
            content=b'{"name": "test", "value": 123}',
        )

        data = await response.json()
        assert data == {"name": "test", "value": 123}

    def test_status_and_ok(self):
        """Test status code and ok property."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response_ok = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={},
            content=b"",
        )
        assert response_ok.ok is True
        assert response_ok.status == 200

        response_error = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=404,
            headers={},
            content=b"",
        )
        assert response_error.ok is False
        assert response_error.status == 404

    def test_raise_for_status(self):
        """Test raise_for_status method."""
        import aiohttp
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=404,
            headers={},
            content=b"",
        )

        with pytest.raises(aiohttp.ClientResponseError):
            response.raise_for_status()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={},
            content=b"test",
        )

        async with response as r:
            body = await r.read()
            assert body == b"test"

    def test_headers(self):
        """Test headers property."""
        from yarl import URL

        from timetracer.plugins.aiohttp_plugin import _MockClientResponse

        response = _MockClientResponse(
            method="GET",
            url=URL("https://example.com"),
            status=200,
            headers={"Content-Type": "application/json", "X-Custom": "value"},
            content=b"{}",
        )

        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-Custom"] == "value"
