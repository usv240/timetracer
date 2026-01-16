"""
Replay engine for Timetracer.

The ReplayEngine manages cassette playback and event matching.
Most functionality is in ReplaySession (session.py), this provides
additional utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from timetracer.cassette import read_cassette
from timetracer.constants import EventType
from timetracer.session import ReplaySession

if TYPE_CHECKING:
    from timetracer.types import Cassette, DependencyEvent


class ReplayEngine:
    """
    Engine for replaying cassettes.

    This is a convenience wrapper around ReplaySession for programmatic use.
    Most applications will use ReplaySession directly via the middleware.
    """

    def __init__(
        self,
        cassette_path: str,
        strict: bool = True,
    ) -> None:
        """
        Initialize replay engine.

        Args:
            cassette_path: Path to the cassette file.
            strict: If True, raise on mismatches.
        """
        self.cassette_path = cassette_path
        self.strict = strict
        self._cassette: Cassette | None = None
        self._session: ReplaySession | None = None

    def load(self) -> None:
        """Load the cassette from disk."""
        self._cassette = read_cassette(self.cassette_path)
        self._session = ReplaySession(
            cassette=self._cassette,
            cassette_path=self.cassette_path,
            strict=self.strict,
        )

    @property
    def cassette(self) -> Cassette:
        """Get loaded cassette."""
        if self._cassette is None:
            raise RuntimeError("Cassette not loaded. Call load() first.")
        return self._cassette

    @property
    def session(self) -> ReplaySession:
        """Get replay session."""
        if self._session is None:
            raise RuntimeError("Session not created. Call load() first.")
        return self._session

    def get_events_by_type(self, event_type: EventType) -> list[DependencyEvent]:
        """Get all events of a specific type."""
        return [e for e in self.cassette.events if e.event_type == event_type]

    def get_http_events(self) -> list[DependencyEvent]:
        """Get all HTTP client events."""
        return self.get_events_by_type(EventType.HTTP_CLIENT)
