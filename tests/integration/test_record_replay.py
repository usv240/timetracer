"""Integration tests for record/replay flow."""

import json
import tempfile
from pathlib import Path

from timetracer.cassette import read_cassette
from timetracer.cassette.io import _dict_to_cassette
from timetracer.config import TraceConfig
from timetracer.constants import TraceMode


class TestCassetteIO:
    """Tests for cassette reading and writing."""

    def test_read_cassette_from_dict(self, sample_cassette_data):
        """Cassette should be loadable from dict."""
        cassette = _dict_to_cassette(sample_cassette_data)

        assert cassette.schema_version == "0.1"  # Not migrated when using _dict_to_cassette directly
        assert cassette.session.id == "test-session-123"
        assert cassette.request.method == "POST"
        assert cassette.request.path == "/checkout"
        assert cassette.response.status == 200
        assert len(cassette.events) == 1

    def test_read_write_cassette(self, sample_cassette_data):
        """Cassette should roundtrip through file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write cassette
            cassette_path = Path(tmpdir) / "test.json"
            with open(cassette_path, "w") as f:
                json.dump(sample_cassette_data, f)

            # Read it back
            cassette = read_cassette(str(cassette_path))

            assert cassette.schema_version == "1.0"  # Migrated from 0.1 to 1.0
            assert cassette.session.service == "test-service"
            assert len(cassette.events) == 1
            assert cassette.events[0].signature.method == "GET"


class TestTraceConfig:
    """Tests for TraceConfig."""

    def test_default_config(self):
        """Default config should have off mode."""
        config = TraceConfig()

        assert config.mode == TraceMode.OFF
        assert config.sample_rate == 1.0

    def test_record_mode(self):
        """Record mode properties should work."""
        config = TraceConfig(mode=TraceMode.RECORD)

        assert config.is_record_mode is True
        assert config.is_replay_mode is False
        assert config.is_enabled is True

    def test_replay_mode(self):
        """Replay mode properties should work."""
        config = TraceConfig(mode=TraceMode.REPLAY)

        assert config.is_record_mode is False
        assert config.is_replay_mode is True
        assert config.is_enabled is True

    def test_should_trace_excludes_health(self):
        """Health endpoint should be excluded."""
        config = TraceConfig()

        assert config.should_trace("/health") is False
        assert config.should_trace("/metrics") is False
        assert config.should_trace("/checkout") is True

    def test_string_mode_conversion(self):
        """String modes should be converted to enum."""
        config = TraceConfig(mode="record")

        assert config.mode == TraceMode.RECORD


class TestReplaySession:
    """Tests for ReplaySession."""

    def test_cursor_management(self, sample_cassette_data):
        """Replay cursor should track consumed events."""
        from timetracer.cassette.io import _dict_to_cassette
        from timetracer.session import ReplaySession

        cassette = _dict_to_cassette(sample_cassette_data)
        session = ReplaySession(
            cassette=cassette,
            cassette_path="/test/path.json",
            strict=False,
        )

        assert session.current_cursor == 0
        assert session.has_more_events is True

        # Peek at next event
        next_event = session.peek_next_event()
        assert next_event is not None
        assert next_event.eid == 1

        # Cursor shouldn't move after peek
        assert session.current_cursor == 0

    def test_event_consumption(self, sample_cassette_data):
        """Events should be consumed in order."""
        from timetracer.cassette.io import _dict_to_cassette
        from timetracer.constants import EventType
        from timetracer.session import ReplaySession

        cassette = _dict_to_cassette(sample_cassette_data)
        session = ReplaySession(
            cassette=cassette,
            cassette_path="/test/path.json",
            strict=True,
        )

        # Get next event
        event = session.get_next_event(
            EventType.HTTP_CLIENT,
            {"method": "GET", "url": "https://api.example.com/data"},
        )

        assert event is not None
        assert event.eid == 1
        assert session.current_cursor == 1
        assert session.has_more_events is False
