"""
Integration tests for Motor/MongoDB plugin.

These tests mock the Motor library to simulate MongoDB behavior,
allowing us to test the plugin without requiring a real MongoDB instance.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from timetracer.config import TraceConfig
from timetracer.constants import EventType, TraceMode
from timetracer.context import reset_session, set_session
from timetracer.session import TraceSession
from timetracer.types import RequestSnapshot, ResponseSnapshot

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def trace_session():
    """Create a real TraceSession for testing."""
    config = TraceConfig(mode=TraceMode.RECORD)
    session = TraceSession(config=config)
    # Use set_request method
    session.set_request(RequestSnapshot(
        method="GET",
        path="/api/test",
        route_template="/api/test",
        headers={},
        query={},
        body=None,
        client_ip="127.0.0.1",
        user_agent="test",
    ))
    token = set_session(session)
    yield session
    reset_session(token)


@pytest.fixture
def mock_motor_collection():
    """
    Create a mock Motor collection that simulates MongoDB behavior.
    
    This allows testing the plugin without a real MongoDB instance.
    """
    # Create mock objects
    collection = MagicMock()
    collection.name = "users"

    # Mock the database
    database = MagicMock()
    database.name = "testdb"
    collection.database = database

    return collection


@pytest.fixture
def mock_insert_result():
    """Create a mock InsertOneResult."""
    result = MagicMock()
    result.inserted_id = "507f1f77bcf86cd799439011"
    result.acknowledged = True
    return result


@pytest.fixture
def mock_update_result():
    """Create a mock UpdateResult."""
    result = MagicMock()
    result.matched_count = 1
    result.modified_count = 1
    result.acknowledged = True
    result.upserted_id = None
    return result


@pytest.fixture
def mock_delete_result():
    """Create a mock DeleteResult."""
    result = MagicMock()
    result.deleted_count = 1
    result.acknowledged = True
    return result


# =============================================================================
# Test Classes
# =============================================================================

class TestMotorPluginRecording:
    """Test that Motor operations are correctly recorded."""

    @pytest.mark.asyncio
    async def test_find_one_is_recorded(
        self, trace_session, mock_motor_collection
    ):
        """Test that find_one operations are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_find_one,
        )

        # Setup mock
        mock_motor_collection.find_one = AsyncMock(
            return_value={"_id": "123", "name": "Test User", "email": "test@example.com"}
        )

        # Mock the original method
        original = AsyncMock(return_value={"_id": "123", "name": "Test User"})
        _original_methods["find_one"] = original

        # Call the patched method
        await _patched_find_one(
            mock_motor_collection,
            {"email": "test@example.com"},
        )

        # Verify the operation was recorded
        events = trace_session.events
        assert len(events) >= 1

        # Find the db.query event
        db_events = [e for e in events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.signature.lib == "motor"
        assert event.signature.method == "FIND_ONE"
        assert event.signature.url == "testdb.users"

    @pytest.mark.asyncio
    async def test_insert_one_is_recorded(
        self, trace_session, mock_motor_collection, mock_insert_result
    ):
        """Test that insert_one operations are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_insert_one,
        )

        # Mock the original method
        original = AsyncMock(return_value=mock_insert_result)
        _original_methods["insert_one"] = original

        # Call the patched method
        result = await _patched_insert_one(
            mock_motor_collection,
            {"name": "New User", "email": "new@example.com"},
        )

        # Verify result
        assert result.inserted_id == "507f1f77bcf86cd799439011"

        # Verify the operation was recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.signature.method == "INSERT_ONE"
        assert event.result.body.data["acknowledged"] == True

    @pytest.mark.asyncio
    async def test_update_one_is_recorded(
        self, trace_session, mock_motor_collection, mock_update_result
    ):
        """Test that update_one operations are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_update_one,
        )

        # Mock the original method
        original = AsyncMock(return_value=mock_update_result)
        _original_methods["update_one"] = original

        # Call the patched method
        result = await _patched_update_one(
            mock_motor_collection,
            {"_id": "123"},
            {"$set": {"name": "Updated Name"}},
        )

        # Verify result
        assert result.modified_count == 1

        # Verify the operation was recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.signature.method == "UPDATE_ONE"
        assert event.result.body.data["matched_count"] == 1
        assert event.result.body.data["modified_count"] == 1

    @pytest.mark.asyncio
    async def test_delete_one_is_recorded(
        self, trace_session, mock_motor_collection, mock_delete_result
    ):
        """Test that delete_one operations are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_delete_one,
        )

        # Mock the original method
        original = AsyncMock(return_value=mock_delete_result)
        _original_methods["delete_one"] = original

        # Call the patched method
        result = await _patched_delete_one(
            mock_motor_collection,
            {"_id": "123"},
        )

        # Verify result
        assert result.deleted_count == 1

        # Verify the operation was recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.signature.method == "DELETE_ONE"
        assert event.result.body.data["deleted_count"] == 1

    @pytest.mark.asyncio
    async def test_count_documents_is_recorded(
        self, trace_session, mock_motor_collection
    ):
        """Test that count_documents operations are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_count_documents,
        )

        # Mock the original method
        original = AsyncMock(return_value=42)
        _original_methods["count_documents"] = original

        # Call the patched method
        result = await _patched_count_documents(
            mock_motor_collection,
            {"active": True},
        )

        # Verify result
        assert result == 42

        # Verify the operation was recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.signature.method == "COUNT_DOCUMENTS"
        assert event.result.body.data["count"] == 42


class TestMotorPluginErrorHandling:
    """Test error handling in Motor plugin."""

    @pytest.mark.asyncio
    async def test_find_one_error_is_recorded(
        self, trace_session, mock_motor_collection
    ):
        """Test that errors in find_one are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_find_one,
        )

        # Mock the original method to raise an error
        original = AsyncMock(side_effect=Exception("Connection failed"))
        _original_methods["find_one"] = original

        # Call should raise
        with pytest.raises(Exception, match="Connection failed"):
            await _patched_find_one(
                mock_motor_collection,
                {"_id": "123"},
            )

        # Verify the error was recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        event = db_events[0]
        assert event.result.error == "Connection failed"
        assert event.result.error_type == "Exception"
        assert event.result.status == -1

    @pytest.mark.asyncio
    async def test_insert_one_error_is_recorded(
        self, trace_session, mock_motor_collection
    ):
        """Test that errors in insert_one are recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_insert_one,
        )

        # Mock duplicate key error
        original = AsyncMock(side_effect=Exception("Duplicate key error"))
        _original_methods["insert_one"] = original

        with pytest.raises(Exception, match="Duplicate key"):
            await _patched_insert_one(
                mock_motor_collection,
                {"_id": "existing"},
            )

        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1
        assert db_events[0].result.error == "Duplicate key error"


class TestMotorPluginTiming:
    """Test timing capture in Motor plugin."""

    @pytest.mark.asyncio
    async def test_duration_is_captured(
        self, trace_session, mock_motor_collection
    ):
        """Test that operation duration is captured."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_find_one,
        )

        # Mock with a small delay
        async def slow_find(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms delay
            return {"_id": "123"}

        original = AsyncMock(side_effect=slow_find)
        _original_methods["find_one"] = original

        await _patched_find_one(mock_motor_collection, {"_id": "123"})

        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 1

        # Duration should be at least 10ms
        assert db_events[0].duration_ms >= 10.0


class TestMotorPluginCassetteSerialization:
    """Test that Motor events serialize correctly to cassettes."""

    @pytest.mark.asyncio
    async def test_event_serializes_to_cassette(
        self, trace_session, mock_motor_collection, mock_insert_result, tmp_path
    ):
        """Test that Motor events can be written to cassettes."""
        from timetracer.cassette.io import read_cassette, write_cassette
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_insert_one,
        )

        # Setup
        original = AsyncMock(return_value=mock_insert_result)
        _original_methods["insert_one"] = original

        # Perform operation
        await _patched_insert_one(
            mock_motor_collection,
            {"name": "Test", "email": "test@example.com"},
        )

        # Finalize and set response
        trace_session.set_response(ResponseSnapshot(
            status=200,
            headers={},
            body=None,
            duration_ms=100.0,
        ))
        trace_session.finalize()

        # Write cassette
        config = TraceConfig(cassette_dir=str(tmp_path))
        cassette_path = write_cassette(trace_session, config)

        # Read back
        cassette = read_cassette(cassette_path)

        # Verify events
        assert len(cassette.events) >= 1
        motor_events = [e for e in cassette.events if e.signature.lib == "motor"]
        assert len(motor_events) == 1
        assert motor_events[0].signature.method == "INSERT_ONE"


class TestMotorPluginMultipleOperations:
    """Test multiple Motor operations in sequence."""

    @pytest.mark.asyncio
    async def test_multiple_operations_recorded(
        self, trace_session, mock_motor_collection, mock_insert_result, mock_update_result
    ):
        """Test that multiple operations are all recorded."""
        from timetracer.plugins.motor_plugin import (
            _original_methods,
            _patched_find_one,
            _patched_insert_one,
            _patched_update_one,
        )

        # Setup mocks
        _original_methods["insert_one"] = AsyncMock(return_value=mock_insert_result)
        _original_methods["find_one"] = AsyncMock(return_value={"_id": "123"})
        _original_methods["update_one"] = AsyncMock(return_value=mock_update_result)

        # Perform multiple operations
        await _patched_insert_one(mock_motor_collection, {"name": "User"})
        await _patched_find_one(mock_motor_collection, {"name": "User"})
        await _patched_update_one(mock_motor_collection, {"name": "User"}, {"$set": {"active": True}})

        # Verify all recorded
        db_events = [e for e in trace_session.events if e.event_type == EventType.DB_QUERY]
        assert len(db_events) == 3

        methods = [e.signature.method for e in db_events]
        assert "INSERT_ONE" in methods
        assert "FIND_ONE" in methods
        assert "UPDATE_ONE" in methods


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
