"""
Centralized type definitions for Timetracer.

All shared types, protocols, and type aliases are defined here.
This ensures type consistency across the codebase.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from timetracer.constants import EventType

# =============================================================================
# REQUEST/RESPONSE SNAPSHOTS
# =============================================================================

@dataclass
class BodySnapshot:
    """Captured body data with metadata."""
    captured: bool
    encoding: str | None = None  # "json", "text", "base64"
    data: Any = None
    truncated: bool = False
    size_bytes: int | None = None
    hash: str | None = None  # sha256 hash for matching


@dataclass
class RequestSnapshot:
    """Captured incoming request data."""
    method: str
    path: str
    route_template: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    body: BodySnapshot | None = None
    client_ip: str | None = None
    user_agent: str | None = None


@dataclass
class ResponseSnapshot:
    """Captured outgoing response data."""
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: BodySnapshot | None = None
    duration_ms: float = 0.0


# =============================================================================
# DEPENDENCY EVENTS
# =============================================================================

@dataclass
class EventSignature:
    """
    Signature used to match dependency calls during replay.

    This contains the minimal information needed to identify a call.
    """
    lib: str  # e.g., "httpx", "sqlalchemy"
    method: str  # HTTP method or operation type
    url: str | None = None  # Normalized URL for HTTP
    query: dict[str, str] = field(default_factory=dict)
    headers_hash: str | None = None  # Hash of relevant headers
    body_hash: str | None = None  # Hash of request body


@dataclass
class EventResult:
    """Result of a dependency call."""
    status: int | None = None  # HTTP status or similar
    headers: dict[str, str] = field(default_factory=dict)
    body: BodySnapshot | None = None
    error: str | None = None
    error_type: str | None = None


@dataclass
class DependencyEvent:
    """
    A captured dependency call (HTTP, DB, etc.).

    This is the core unit stored in cassettes.
    """
    eid: int  # Sequential event ID within the session
    event_type: EventType
    start_offset_ms: float  # Time since request start
    duration_ms: float
    signature: EventSignature
    result: EventResult


# =============================================================================
# SESSION METADATA
# =============================================================================

@dataclass
class SessionMeta:
    """Metadata about the recording session."""
    id: str  # UUID
    recorded_at: str  # ISO-8601 timestamp
    service: str
    env: str
    framework: str = "fastapi"
    timetracer_version: str = ""
    python_version: str = ""
    git_sha: str | None = None


@dataclass
class CaptureStats:
    """Statistics about what was captured."""
    event_counts: dict[str, int] = field(default_factory=dict)
    total_events: int = 0
    total_duration_ms: float = 0.0


@dataclass
class AppliedPolicies:
    """Record of which policies were applied during capture."""
    redaction_mode: str = "default"
    redaction_rules: list[str] = field(default_factory=list)
    max_body_kb: int = 64
    store_request_body: str = "on_error"
    store_response_body: str = "on_error"
    sample_rate: float = 1.0
    errors_only: bool = False


# =============================================================================
# CASSETTE (TOP-LEVEL STRUCTURE)
# =============================================================================

@dataclass
class Cassette:
    """
    Complete cassette structure.

    This is the portable artifact that gets saved/loaded.
    """
    schema_version: str
    session: SessionMeta
    request: RequestSnapshot
    response: ResponseSnapshot
    events: list[DependencyEvent] = field(default_factory=list)
    policies: AppliedPolicies = field(default_factory=AppliedPolicies)
    stats: CaptureStats = field(default_factory=CaptureStats)
    error_info: dict[str, Any] | None = None  # Stack trace, error type, message


# =============================================================================
# PLUGIN PROTOCOL
# =============================================================================

@runtime_checkable
class TracePlugin(Protocol):
    """
    Protocol for Timetracer plugins.

    Plugins must implement this interface to integrate with the system.
    """

    @property
    def name(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    def event_type(self) -> EventType:
        """The type of events this plugin captures."""
        ...

    def setup(self, config: Any) -> None:
        """Initialize the plugin with configuration."""
        ...

    def enable_recording(self) -> None:
        """Start capturing events."""
        ...

    def enable_replay(self) -> None:
        """Start mocking calls with recorded data."""
        ...

    def disable(self) -> None:
        """Stop capturing/mocking and restore original behavior."""
        ...


# =============================================================================
# TYPE ALIASES
# =============================================================================

HeadersDict = dict[str, str]
QueryDict = dict[str, str]
JsonDict = dict[str, Any]
