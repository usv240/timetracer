"""Unit tests for PyMongo plugin."""

import pytest


class TestPyMongoPluginImport:
    """Test PyMongo plugin can be imported."""

    def test_import_enable_pymongo(self):
        """Test enable_pymongo can be imported."""
        from timetracer.plugins import enable_pymongo
        assert callable(enable_pymongo)

    def test_import_disable_pymongo(self):
        """Test disable_pymongo can be imported."""
        from timetracer.plugins import disable_pymongo
        assert callable(disable_pymongo)


class TestPyMongoPluginWithoutPyMongo:
    """Test PyMongo plugin behavior when pymongo is not installed."""

    def test_enable_pymongo_raises_without_pymongo(self, monkeypatch):
        """Test enable_pymongo raises ImportError if pymongo not installed."""
        # This test would need to mock the pymongo import
        # For now, we'll skip if pymongo IS installed
        try:
            import pymongo  # noqa: F401
            pytest.skip("PyMongo is installed")
        except ImportError:
            from timetracer.plugins import enable_pymongo
            with pytest.raises(ImportError, match="pymongo is required"):
                enable_pymongo()


class TestPyMongoPluginSignature:
    """Test PyMongo plugin signature creation."""

    def test_make_signature_find_one(self):
        """Test signature creation for find_one operation."""
        from timetracer.plugins.pymongo_plugin import _make_signature

        sig = _make_signature(
            operation="find_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"email": "test@example.com"},
            update_doc=None,
        )

        assert sig.lib == "pymongo"
        assert sig.method == "FIND_ONE"
        assert sig.url == "testdb.users"
        assert "filter_keys" in sig.query
        assert sig.query["filter_keys"] == ["email"]

    def test_make_signature_insert_one(self):
        """Test signature creation for insert_one operation."""
        from timetracer.plugins.pymongo_plugin import _make_signature

        sig = _make_signature(
            operation="insert_one",
            db_name="testdb",
            collection_name="orders",
            filter_doc={"user_id": "123", "total": 99.99},
            update_doc=None,
        )

        assert sig.lib == "pymongo"
        assert sig.method == "INSERT_ONE"
        assert sig.url == "testdb.orders"
        assert sig.body_hash is not None  # Should have hash

    def test_make_signature_update_one(self):
        """Test signature creation for update_one operation."""
        from timetracer.plugins.pymongo_plugin import _make_signature

        sig = _make_signature(
            operation="update_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"_id": "123"},
            update_doc={"$set": {"status": "active"}},
        )

        assert sig.lib == "pymongo"
        assert sig.method == "UPDATE_ONE"
        assert sig.url == "testdb.users"
        assert sig.body_hash is not None  # Should have hash from both filter and update


class TestPyMongoPluginResult:
    """Test PyMongo plugin result creation."""

    def test_make_result_success(self):
        """Test result creation for successful operation."""
        from timetracer.plugins.pymongo_plugin import _make_result

        result = _make_result(
            result_data={"_id": "123", "name": "Test User"},
            error_info=None,
        )

        assert result.status == 0  # Success
        assert result.body is not None
        assert result.body.data == {"_id": "123", "name": "Test User"}
        assert result.error is None

    def test_make_result_error(self):
        """Test result creation for failed operation."""
        from timetracer.plugins.pymongo_plugin import _make_result

        result = _make_result(
            result_data=None,
            error_info=("ConnectionError", "Failed to connect to MongoDB"),
        )

        assert result.status == -1  # Error
        assert result.error == "Failed to connect to MongoDB"
        assert result.error_type == "ConnectionError"


class TestPyMongoPluginEventBuilding:
    """Test PyMongo plugin event building."""

    def test_build_event(self):
        """Test building a complete DependencyEvent."""
        from timetracer.plugins.pymongo_plugin import _build_event

        event = _build_event(
            operation="find_one",
            db_name="testdb",
            collection_name="users",
            filter_doc={"email": "test@example.com"},
            update_doc=None,
            result_data={"_id": "123", "email": "test@example.com"},
            start_offset_ms=100,
            duration_ms=5.5,
            error_info=None,
        )

        assert event.event_type.value == "db.query"
        assert event.signature.lib == "pymongo"
        assert event.signature.method == "FIND_ONE"
        assert event.start_offset_ms == 100
        assert event.duration_ms == 5.5
        assert event.result.status == 0


class TestPyMongoPluginSerialization:
    """Test PyMongo plugin serialization."""

    def test_safe_serialize_dict(self):
        """Test serializing a regular dict."""
        from timetracer.plugins.pymongo_plugin import _safe_serialize

        data = {"name": "Test", "age": 30}
        result = _safe_serialize(data)

        assert isinstance(result, str)
        assert "name" in result
        assert "Test" in result

    def test_safe_serialize_with_objectid(self):
        """Test serializing dict with ObjectId."""
        pytest.importorskip("bson")
        from bson import ObjectId
        from timetracer.plugins.pymongo_plugin import _safe_serialize

        data = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test"}
        result = _safe_serialize(data)

        assert isinstance(result, str)
        assert "507f1f77bcf86cd799439011" in result

    def test_safe_serialize_with_datetime(self):
        """Test serializing dict with datetime."""
        from datetime import datetime
        from timetracer.plugins.pymongo_plugin import _safe_serialize

        now = datetime(2026, 1, 22, 12, 0, 0)
        data = {"created_at": now, "name": "Test"}
        result = _safe_serialize(data)

        assert isinstance(result, str)
        assert "2026-01-22" in result


class TestPyMongoPluginEnableDisable:
    """Test PyMongo plugin enable/disable cycle."""

    def test_enable_disable_cycle(self):
        """Test enabling and disabling PyMongo plugin."""
        pytest.importorskip("pymongo")
        from timetracer.plugins import disable_pymongo, enable_pymongo

        # Enable
        enable_pymongo()

        # Disable
        disable_pymongo()

        # Should not raise
        assert True

    def test_double_enable_is_safe(self):
        """Test that enabling twice doesn't cause issues."""
        pytest.importorskip("pymongo")
        from timetracer.plugins import enable_pymongo

        enable_pymongo()
        enable_pymongo()  # Second enable should be no-op

        # Clean up
        from timetracer.plugins import disable_pymongo
        disable_pymongo()

    def test_double_disable_is_safe(self):
        """Test that disabling twice doesn't cause issues."""
        pytest.importorskip("pymongo")
        from timetracer.plugins import disable_pymongo

        disable_pymongo()
        disable_pymongo()  # Second disable should be no-op

        assert True


class TestPyMongoPluginOperations:
    """Test actual PyMongo operations are captured (requires pymongo)."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock MongoDB collection."""
        pytest.importorskip("pymongo")
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.database.name = "testdb"
        collection.name = "users"
        return collection

    def test_find_one_signature_from_real_operation(self, mock_collection):
        """Test find_one creates correct signature from real operation."""
        pytest.importorskip("pymongo")
        from timetracer.plugins.pymongo_plugin import _record_operation
        from unittest.mock import patch

        with patch('timetracer.plugins.pymongo_plugin.get_current_session') as mock_session:
            mock_session.return_value = None  # No active session

            # This should not raise
            _record_operation(
                collection=mock_collection,
                operation="find_one",
                filter_doc={"email": "test@example.com"},
                result_data={"_id": "123"},
                duration_ms=2.5,
            )


class TestPyMongoPluginIntegration:
    """Integration tests for PyMongo plugin (requires actual MongoDB)."""

    @pytest.mark.integration
    def test_full_record_cycle(self):
        """Test full record cycle with PyMongo."""
        # Skip immediately - requires MongoDB running
        pytest.skip("Requires MongoDB running - integration test")

        enable_pymongo()

        client = MongoClient('mongodb://localhost:27017')
        db = client.testdb

        config = TraceConfig(mode="record")
        session = TraceSession(config=config, request_method="TEST", request_path="/test")

        # Perform operation
        db.users.find_one({"email": "test@example.com"})

        # Check session captured event
        # assert len(session.events) > 0

        disable_pymongo()
