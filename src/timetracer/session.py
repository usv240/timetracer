"""
Session management for Timetracer.

Sessions hold all captured data for a single request lifecycle.
- TraceSession: Used in record mode to collect events
- ReplaySession: Used in replay mode to serve recorded events
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from timetracer import __version__
from timetracer.constants import SCHEMA_VERSION, EventType, TraceMode
from timetracer.exceptions import ReplayMismatchError
from timetracer.types import (
    AppliedPolicies,
    CaptureStats,
    Cassette,
    DependencyEvent,
    RequestSnapshot,
    ResponseSnapshot,
    SessionMeta,
)

if TYPE_CHECKING:
    from timetracer.config import TraceConfig


class BaseSession(ABC):
    """
    Abstract base class for all session types.

    This provides a common interface for both record and replay modes.
    """

    @property
    @abstractmethod
    def mode(self) -> TraceMode:
        """The mode this session operates in."""
        ...

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Unique identifier for this session."""
        ...

    @property
    @abstractmethod
    def is_recording(self) -> bool:
        """True if this session is recording events."""
        ...

    @property
    @abstractmethod
    def is_replaying(self) -> bool:
        """True if this session is replaying from cassette."""
        ...


@dataclass
class TraceSession(BaseSession):
    """
    Session for record mode.

    Collects request/response data and dependency events during execution.
    Finalized into a Cassette for storage.
    """

    config: TraceConfig

    # Session identity
    _session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _start_time: float = field(default_factory=time.perf_counter)
    _start_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Captured data
    request: RequestSnapshot | None = None
    response: ResponseSnapshot | None = None
    events: list[DependencyEvent] = field(default_factory=list)

    # State tracking
    _event_counter: int = 0
    _is_error: bool = False
    _error_info: dict[str, Any] | None = None
    _finalized: bool = False

    @property
    def mode(self) -> TraceMode:
        return TraceMode.RECORD

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def short_id(self) -> str:
        """Short version of session ID for filenames."""
        return self._session_id[:8]

    @property
    def is_recording(self) -> bool:
        return True

    @property
    def is_replaying(self) -> bool:
        return False

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds since session started."""
        return (time.perf_counter() - self._start_time) * 1000

    def set_request(self, request: RequestSnapshot) -> None:
        """Set the captured request data."""
        self.request = request

    def set_response(self, response: ResponseSnapshot) -> None:
        """Set the captured response data."""
        self.response = response

    def add_event(self, event: DependencyEvent) -> None:
        """
        Add a captured dependency event.

        Events are automatically assigned sequential IDs.
        """
        if self._finalized:
            raise RuntimeError("Cannot add events to a finalized session")

        # Assign event ID
        self._event_counter += 1
        event.eid = self._event_counter

        self.events.append(event)

    def mark_error(
        self,
        error_type: str,
        error_message: str,
        traceback: str | None = None
    ) -> None:
        """Mark session as having an error."""
        self._is_error = True
        self._error_info = {
            "type": error_type,
            "message": error_message,
        }
        if traceback:
            self._error_info["traceback"] = traceback

    @property
    def has_error(self) -> bool:
        """Check if this session has an error."""
        return self._is_error

    def finalize(self) -> None:
        """Mark session as complete. No more events can be added."""
        self._finalized = True

    def to_cassette(self) -> Cassette:
        """
        Convert session to a Cassette for storage.

        This should be called after finalize().
        """
        # Build session metadata
        session_meta = SessionMeta(
            id=self._session_id,
            recorded_at=self._start_timestamp,
            service=self.config.service_name,
            env=self.config.env,
            framework="fastapi",
            timetracer_version=__version__,
            python_version=self.config.get_python_version(),
        )

        # Build stats
        event_counts: dict[str, int] = {}
        for event in self.events:
            event_type_str = event.event_type.value
            event_counts[event_type_str] = event_counts.get(event_type_str, 0) + 1

        stats = CaptureStats(
            event_counts=event_counts,
            total_events=len(self.events),
            total_duration_ms=self.response.duration_ms if self.response else self.elapsed_ms,
        )

        # Build applied policies
        policies = AppliedPolicies(
            redaction_mode="default",
            redaction_rules=["authorization", "cookie"],
            max_body_kb=self.config.max_body_kb,
            store_request_body=self.config.store_request_body.value,
            store_response_body=self.config.store_response_body.value,
            sample_rate=self.config.sample_rate,
            errors_only=self.config.errors_only,
        )

        return Cassette(
            schema_version=SCHEMA_VERSION,
            session=session_meta,
            request=self.request or RequestSnapshot(method="", path=""),
            response=self.response or ResponseSnapshot(status=0),
            events=self.events,
            policies=policies,
            stats=stats,
            error_info=self._error_info if self._is_error else None,
        )


@dataclass
class ReplaySession(BaseSession):
    """
    Session for replay mode.

    Loads a cassette and serves recorded events during execution.
    Uses order-first matching to return expected responses.
    """

    cassette: Cassette
    cassette_path: str
    strict: bool = True
    config: TraceConfig | None = None  # For hybrid replay

    # Replay cursor
    _cursor: int = 0
    _consumed_events: list[int] = field(default_factory=list)

    @property
    def mode(self) -> TraceMode:
        return TraceMode.REPLAY

    @property
    def session_id(self) -> str:
        return self.cassette.session.id

    @property
    def is_recording(self) -> bool:
        return False

    @property
    def is_replaying(self) -> bool:
        return True

    @property
    def request(self) -> RequestSnapshot:
        """The recorded request."""
        return self.cassette.request

    @property
    def events(self) -> list[DependencyEvent]:
        """All recorded events."""
        return self.cassette.events

    def should_mock_plugin(self, plugin_name: str) -> bool:
        """
        Check if a plugin should be mocked in this replay session.

        This enables hybrid replay where some dependencies are mocked
        and others are kept live.

        Args:
            plugin_name: The plugin name (e.g., "http", "db")

        Returns:
            True if the plugin should be mocked, False to keep live.
        """
        if self.config is None:
            return True  # Default: mock everything
        return self.config.should_mock_plugin(plugin_name)

    @property
    def current_cursor(self) -> int:
        """Current position in event list."""
        return self._cursor

    @property
    def has_more_events(self) -> bool:
        """Check if there are unmatched events remaining."""
        return self._cursor < len(self.cassette.events)

    def peek_next_event(self, event_type: EventType | None = None) -> DependencyEvent | None:
        """
        Look at the next expected event without consuming it.

        Args:
            event_type: Optionally filter by event type.

        Returns:
            The next event, or None if no matching event.
        """
        if self._cursor >= len(self.cassette.events):
            return None

        event = self.cassette.events[self._cursor]

        if event_type is not None and event.event_type != event_type:
            return None

        return event

    def get_next_event(
        self,
        event_type: EventType,
        actual_signature: dict[str, Any],
    ) -> DependencyEvent:
        """
        Get the next expected event for matching.

        This validates that the actual call matches the expected call.
        Raises ReplayMismatchError if there's a mismatch and strict=True.

        Args:
            event_type: Expected event type.
            actual_signature: Signature of the actual call being made.

        Returns:
            The matched event from the cassette.

        Raises:
            ReplayMismatchError: If call doesn't match expected (in strict mode).
        """
        if self._cursor >= len(self.cassette.events):
            if self.strict:
                raise ReplayMismatchError(
                    f"Unexpected {event_type.value} call: no more events in cassette",
                    cassette_path=self.cassette_path,
                    endpoint=f"{self.cassette.request.method} {self.cassette.request.path}",
                    event_index=self._cursor,
                    actual=actual_signature,
                    hint="Your code is making more dependency calls than recorded. Re-record the cassette.",
                )
            return None  # type: ignore

        expected = self.cassette.events[self._cursor]

        # Validate event type
        if expected.event_type != event_type:
            if self.strict:
                raise ReplayMismatchError(
                    f"Event type mismatch at event #{self._cursor}",
                    cassette_path=self.cassette_path,
                    endpoint=f"{self.cassette.request.method} {self.cassette.request.path}",
                    event_index=self._cursor,
                    expected={"type": expected.event_type.value},
                    actual={"type": event_type.value},
                    hint="Call order or type has changed. Re-record the cassette.",
                )
            return None  # type: ignore

        # Validate signature (basic matching)
        expected_sig = expected.signature
        mismatches: dict[str, tuple[Any, Any]] = {}

        if "method" in actual_signature and expected_sig.method != actual_signature["method"]:
            mismatches["method"] = (expected_sig.method, actual_signature["method"])

        if "url" in actual_signature and expected_sig.url != actual_signature.get("url"):
            mismatches["url"] = (expected_sig.url, actual_signature.get("url"))

        if mismatches and self.strict:
            raise ReplayMismatchError(
                f"{event_type.value} mismatch at event #{self._cursor}",
                cassette_path=self.cassette_path,
                endpoint=f"{self.cassette.request.method} {self.cassette.request.path}",
                event_index=self._cursor,
                expected={k: v[0] for k, v in mismatches.items()},
                actual={k: v[1] for k, v in mismatches.items()},
                hint="Your dependency call changed (endpoint/method). Re-record cassette or disable strict replay.",
            )

        # Consume the event
        self._consumed_events.append(self._cursor)
        self._cursor += 1

        return expected

    def get_unconsumed_events(self) -> list[DependencyEvent]:
        """Get list of events that weren't matched during replay."""
        return self.cassette.events[self._cursor:]
