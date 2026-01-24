"""
Tests for Motor/MongoDB plugin.

Tests the async MongoDB plugin for recording operations.
Note: These tests mock Motor since we may not have a real MongoDB instance.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestMotorPluginImport:
    """Test that motor plugin can be imported."""

    def test_import_enable_motor(self):
        """Should be able to import enable_motor."""
        from timetracer.plugins import enable_motor
        assert callable(enable_motor)

    def test_import_disable_motor(self):
        """Should be able to import disable_motor."""
        from timetracer.plugins import disable_motor
        assert callable(disable_motor)


class TestMotorPluginWithoutMotor:
    """Test motor plugin behavior when motor is not installed."""

    def test_enable_motor_raises_without_motor(self, monkeypatch):
        """enable_motor should raise ImportError if motor not installed."""
        # Simulate motor not being installed
        import timetracer.plugins.motor_plugin as motor_plugin

        # Save original
        original_enabled = motor_plugin._enabled
        motor_plugin._enabled = False

        # Mock import to fail
        with patch.dict('sys.modules', {'motor': None, 'motor.motor_asyncio': None}):
            # Reset the module to test import behavior
            with pytest.raises(ImportError, match="motor is required"):
                # Force reimport
                import importlib
                importlib.reload(motor_plugin)
                motor_plugin.enable_motor()

        # Restore
        motor_plugin._enabled = original_enabled


class TestMotorPluginSignature:
    """Test signature creation for MongoDB operations."""

    def test_make_signature_find_one(self):
        """Test signature creation for find_one."""
        from timetracer.plugins.motor_plugin import _make_signature

        sig = _make_signature(
            operation="find_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"_id": "123", "active": True},
            update_doc=None,
        )

        assert sig.lib == "motor"
        assert sig.method == "FIND_ONE"
        assert sig.url == "testdb.users"
        assert "filter_keys" in sig.query
        assert sorted(sig.query["filter_keys"]) == ["_id", "active"]

    def test_make_signature_update_one(self):
        """Test signature creation for update_one."""
        from timetracer.plugins.motor_plugin import _make_signature

        sig = _make_signature(
            operation="update_one",
            db_name="mydb",
            collection_name="orders",
            filter_doc={"order_id": "abc"},
            update_doc={"$set": {"status": "shipped"}},
        )

        assert sig.lib == "motor"
        assert sig.method == "UPDATE_ONE"
        assert sig.url == "mydb.orders"
        assert sig.body_hash is not None  # Should have hash of filter+update

    def test_make_signature_insert_one(self):
        """Test signature creation for insert_one."""
        from timetracer.plugins.motor_plugin import _make_signature

        sig = _make_signature(
            operation="insert_one",
            db_name="testdb",
            collection_name="logs",
            filter_doc={"message": "test", "level": "info"},
            update_doc=None,
        )

        assert sig.lib == "motor"
        assert sig.method == "INSERT_ONE"
        assert sig.url == "testdb.logs"


class TestMotorPluginResult:
    """Test result creation for MongoDB operations."""

    def test_make_result_success(self):
        """Test result creation for successful operation."""
        from timetracer.plugins.motor_plugin import _make_result

        result = _make_result(
            result_data={"inserted_id": "123", "acknowledged": True},
            error_info=None,
        )

        assert result.status == 0
        assert result.error is None
        assert result.body is not None
        assert result.body.data["inserted_id"] == "123"

    def test_make_result_error(self):
        """Test result creation for failed operation."""
        from timetracer.plugins.motor_plugin import _make_result

        result = _make_result(
            result_data=None,
            error_info=("DuplicateKeyError", "Duplicate key error"),
        )

        assert result.status == -1
        assert result.error == "Duplicate key error"
        assert result.error_type == "DuplicateKeyError"


class TestMotorPluginEventBuilding:
    """Test event building for MongoDB operations."""

    def test_build_event(self):
        """Test building a complete DependencyEvent."""
        from timetracer.constants import EventType
        from timetracer.plugins.motor_plugin import _build_event

        event = _build_event(
            operation="find_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"name": "test"},
            update_doc=None,
            result_data={"_id": "123", "name": "test"},
            start_offset_ms=100.0,
            duration_ms=5.5,
            error_info=None,
        )

        assert event.event_type == EventType.DB_QUERY
        assert event.start_offset_ms == 100.0
        assert event.duration_ms == 5.5
        assert event.signature.lib == "motor"
        assert event.signature.method == "FIND_ONE"
        assert event.signature.url == "testdb.users"
        assert event.result.status == 0


class TestMotorPluginSerialization:
    """Test safe serialization of MongoDB documents."""

    def test_safe_serialize_dict(self):
        """Test serializing a simple dict."""
        from timetracer.plugins.motor_plugin import _safe_serialize

        result = _safe_serialize({"name": "test", "count": 42})
        assert "name" in result
        assert "test" in result

    def test_safe_serialize_with_objectid(self):
        """Test serializing with ObjectId (mocked)."""
        from timetracer.plugins.motor_plugin import _safe_serialize

        # Mock ObjectId
        class MockObjectId:
            def __str__(self):
                return "507f1f77bcf86cd799439011"

        result = _safe_serialize({"_id": MockObjectId(), "name": "test"})
        assert "507f1f77bcf86cd799439011" in result

    def test_safe_serialize_with_datetime(self):
        """Test serializing with datetime."""
        from datetime import datetime

        from timetracer.plugins.motor_plugin import _safe_serialize

        dt = datetime(2026, 1, 22, 12, 0, 0)
        result = _safe_serialize({"created_at": dt})
        assert "2026-01-22" in result


class TestMotorPluginEnableDisable:
    """Test enabling and disabling the motor plugin."""

    def test_enable_disable_cycle(self):
        """Test that enable/disable cycle works without error."""
        from timetracer.plugins.motor_plugin import disable_motor

        # Disable to known state
        disable_motor()

        # After disable, _enabled should be False
        from timetracer.plugins import motor_plugin
        assert not motor_plugin._enabled

    def test_double_disable_is_safe(self):
        """Double disable should not raise."""
        from timetracer.plugins.motor_plugin import disable_motor

        disable_motor()
        disable_motor()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
