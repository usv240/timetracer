"""
Tests for the Motor/MongoDB example.

These tests verify the plugin loads correctly and functions work.
No actual MongoDB connection required.
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from timetracer.constants import EventType
from timetracer.plugins.motor_plugin import (
    _build_event,
    _make_result,
    _make_signature,
    _safe_serialize,
    disable_motor,
)


class TestMotorPluginLoading:
    """Test that the motor plugin loads correctly."""

    def test_plugin_can_be_imported(self):
        """Plugin should be importable."""
        from timetracer.plugins import enable_motor, disable_motor
        assert callable(enable_motor)
        assert callable(disable_motor)

    def test_disable_is_safe_without_enable(self):
        """Disabling without enabling should not error."""
        disable_motor()
        disable_motor()  # Double disable also safe


class TestSignatureCreation:
    """Test MongoDB operation signature creation."""

    def test_find_one_signature(self):
        """Test find_one operation signature."""
        sig = _make_signature(
            operation="find_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"email": "test@example.com"},
            update_doc=None,
        )

        assert sig.lib == "motor"
        assert sig.method == "FIND_ONE"
        assert sig.url == "testdb.users"
        assert sig.query.get("filter_keys") == ["email"]

    def test_update_one_signature(self):
        """Test update_one operation signature."""
        sig = _make_signature(
            operation="update_one",
            db_name="app",
            collection_name="settings",
            filter_doc={"key": "theme"},
            update_doc={"$set": {"value": "dark"}},
        )

        assert sig.method == "UPDATE_ONE"
        assert sig.url == "app.settings"
        assert sig.body_hash is not None  # Has hash of filter+update

    def test_insert_one_signature(self):
        """Test insert_one operation signature."""
        sig = _make_signature(
            operation="insert_one",
            db_name="blog",
            collection_name="posts",
            filter_doc={"title": "Hello", "content": "World"},
            update_doc=None,
        )

        assert sig.method == "INSERT_ONE"
        assert sig.url == "blog.posts"


class TestResultCreation:
    """Test MongoDB operation result creation."""

    def test_success_result(self):
        """Test successful operation result."""
        result = _make_result(
            result_data={"matched_count": 1, "modified_count": 1},
            error_info=None,
        )

        assert result.status == 0
        assert result.error is None
        assert result.body.data["matched_count"] == 1

    def test_error_result(self):
        """Test error operation result."""
        result = _make_result(
            result_data=None,
            error_info=("WriteError", "Write concern failed"),
        )

        assert result.status == -1
        assert result.error == "Write concern failed"
        assert result.error_type == "WriteError"


class TestEventBuilding:
    """Test complete event building."""

    def test_build_complete_event(self):
        """Test building a complete DependencyEvent."""
        event = _build_event(
            operation="delete_one",
            db_name="mydb",
            collection_name="temp",
            filter_doc={"expired": True},
            update_doc=None,
            result_data={"deleted_count": 5},
            start_offset_ms=50.0,
            duration_ms=3.2,
            error_info=None,
        )

        assert event.event_type == EventType.DB_QUERY
        assert event.start_offset_ms == 50.0
        assert event.duration_ms == 3.2
        assert event.signature.lib == "motor"
        assert event.signature.method == "DELETE_ONE"
        assert event.result.body.data["deleted_count"] == 5


class TestSerialization:
    """Test safe serialization of MongoDB values."""

    def test_serialize_simple_dict(self):
        """Test simple dict serialization."""
        result = _safe_serialize({"name": "test", "value": 123})
        assert '"name"' in result
        assert '"test"' in result
        assert "123" in result

    def test_serialize_datetime(self):
        """Test datetime serialization."""
        from datetime import datetime

        dt = datetime(2026, 1, 22, 12, 30, 0)
        result = _safe_serialize({"timestamp": dt})
        assert "2026-01-22" in result

    def test_serialize_nested(self):
        """Test nested structure serialization."""
        doc = {
            "user": {
                "profile": {
                    "settings": {"theme": "dark"}
                }
            }
        }
        result = _safe_serialize(doc)
        assert "dark" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
