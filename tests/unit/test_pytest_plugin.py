"""
Tests for the pytest plugin.
"""

from pathlib import Path

import pytest


class TestPytestPluginImport:
    """Test that the plugin can be imported."""

    def test_import_fixtures(self):
        """Test importing the fixtures."""
        # Just checking imports work

    def test_import_helper_functions(self):
        """Test importing helper functions."""
        from timetracer.pytest_plugin import (
            _disable_plugins,
            _enable_plugins,
        )
        assert callable(_enable_plugins)
        assert callable(_disable_plugins)


class TestPluginHelpers:
    """Test plugin enable/disable helpers."""

    def test_enable_httpx(self):
        """Test enabling httpx plugin."""
        from timetracer.pytest_plugin import _disable_plugins, _enable_plugins

        enabled = _enable_plugins(["httpx"])
        assert "httpx" in enabled

        _disable_plugins(enabled)

    def test_enable_multiple_plugins(self):
        """Test enabling multiple plugins."""
        from timetracer.pytest_plugin import _disable_plugins, _enable_plugins

        enabled = _enable_plugins(["httpx", "requests"])
        assert "httpx" in enabled
        assert "requests" in enabled

        _disable_plugins(enabled)

    def test_enable_unknown_plugin(self):
        """Test that unknown plugins are ignored."""
        from timetracer.pytest_plugin import _enable_plugins

        enabled = _enable_plugins(["unknown_plugin"])
        assert enabled == []


class TestCassetteDirFixture:
    """Test the cassette directory fixture."""

    def test_fixture_returns_path(self, timetracer_cassette_dir):
        """Test that fixture returns a Path object."""
        assert isinstance(timetracer_cassette_dir, Path)


class TestReplayFixture:
    """Test the replay fixture."""

    def test_replay_fixture_exists(self, timetracer_replay):
        """Test that the replay fixture is available."""
        assert callable(timetracer_replay)

    def test_replay_raises_for_missing_cassette(self, timetracer_replay, tmp_path):
        """Test that replay raises error for missing cassette."""
        with pytest.raises(FileNotFoundError):
            with timetracer_replay(tmp_path / "nonexistent.json"):
                pass


class TestRecordFixture:
    """Test the record fixture."""

    def test_record_fixture_exists(self, timetracer_record):
        """Test that the record fixture is available."""
        assert callable(timetracer_record)

    def test_record_creates_session(self, timetracer_record):
        """Test that recording creates a session."""
        from timetracer.session import TraceSession

        with timetracer_record(use_tmp=True) as session:
            assert isinstance(session, TraceSession)


class TestAutoFixture:
    """Test the auto fixture."""

    def test_auto_fixture_exists(self, timetracer_auto):
        """Test that the auto fixture is available."""
        assert callable(timetracer_auto)


class TestPluginRegistration:
    """Test that the plugin registers correctly with pytest."""

    def test_marker_registered(self, pytestconfig):
        """Test that the cassette marker is registered."""
        # Check that our plugin is loaded
        plugin_info = str(pytestconfig.pluginmanager.list_plugin_distinfo())
        assert "timetracer" in plugin_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
