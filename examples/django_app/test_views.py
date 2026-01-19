"""
Tests for Django example app.

Uses the Timetracer pytest plugin fixtures.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Skip entire module if Django not installed
pytest.importorskip("django")

# Configure Django before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def temp_cassette_dir():
    """Temporary cassette directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDjangoViews:
    """Test Django views."""

    def test_health_endpoint(self, client):
        """Test health check."""
        response = client.get('/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'ok'
        assert data['framework'] == 'django'

    def test_users_list(self, client):
        """Test users list."""
        response = client.get('/api/users/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'users' in data
        assert len(data['users']) == 3


class TestDjangoWithTimetracer:
    """Test Django with Timetracer."""

    def test_record_external_call(self, client, temp_cassette_dir):
        """Test recording external API calls."""
        from timetracer.plugins import disable_requests, enable_requests

        pytest.importorskip("requests")

        enable_requests()
        try:
            response = client.get('/api/fetch-external/')
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['status'] == 'success'
        finally:
            disable_requests()

    def test_middleware_import(self):
        """Test middleware import."""
        from timetracer.integrations.django import TimeTracerMiddleware
        assert TimeTracerMiddleware is not None

    def test_auto_setup_import(self):
        """Test auto_setup import."""
        from timetracer.integrations.django import auto_setup
        assert callable(auto_setup)


class TestDjangoPytestFixtures:
    """Test pytest fixtures with Django."""

    def test_replay_fixture_available(self, timetracer_replay):
        """Replay fixture should be available."""
        assert callable(timetracer_replay)

    def test_record_fixture_available(self, timetracer_record):
        """Record fixture should be available."""
        assert callable(timetracer_record)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
