"""
Centralized constants for Timetracer.

All magic strings, default values, and configuration constants live here.
This ensures consistency and makes future changes easy.
"""

from enum import Enum
from typing import Final

# =============================================================================
# SCHEMA VERSION - bump this when cassette format changes
# =============================================================================
SCHEMA_VERSION: Final[str] = "1.0"
SUPPORTED_SCHEMA_VERSIONS: Final[tuple[str, ...]] = ("0.1", "1.0")

# =============================================================================
# MODE CONSTANTS
# =============================================================================
class TraceMode(str, Enum):
    """Operating mode for Timetracer."""
    OFF = "off"
    RECORD = "record"
    REPLAY = "replay"

# =============================================================================
# BODY CAPTURE POLICY
# =============================================================================
class CapturePolicy(str, Enum):
    """When to capture request/response bodies."""
    NEVER = "never"
    ON_ERROR = "on_error"
    ALWAYS = "always"

# =============================================================================
# EVENT TYPES - centralized so plugins use consistent naming
# =============================================================================
class EventType(str, Enum):
    """Types of dependency events that can be captured."""
    HTTP_CLIENT = "http.client"
    DB_QUERY = "db.query"
    REDIS = "redis"
    CUSTOM = "custom"

# =============================================================================
# DEFAULT VALUES - single source of truth
# =============================================================================
class Defaults:
    """Default configuration values."""
    MODE: TraceMode = TraceMode.OFF
    SERVICE_NAME: str = "timetracer-service"
    ENV: str = "local"
    CASSETTE_DIR: str = "./cassettes"
    SAMPLE_RATE: float = 1.0
    ERRORS_ONLY: bool = False
    MAX_BODY_KB: int = 64
    STORE_REQUEST_BODY: CapturePolicy = CapturePolicy.ON_ERROR
    STORE_RESPONSE_BODY: CapturePolicy = CapturePolicy.ON_ERROR
    STRICT_REPLAY: bool = True
    LOG_LEVEL: str = "info"
    EXCLUDE_PATHS: tuple[str, ...] = ("/health", "/metrics", "/docs", "/openapi.json")

# =============================================================================
# REDACTION CONSTANTS - headers to always remove
# =============================================================================
class Redaction:
    """Redaction rules."""
    # Headers that are ALWAYS removed (case-insensitive matching)
    SENSITIVE_HEADERS: frozenset[str] = frozenset({
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-access-token",
    })

    # Body keys that should be masked (case-insensitive substring matching)
    SENSITIVE_BODY_KEYS: frozenset[str] = frozenset({
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "private_key",
        "credit_card",
        "ssn",
    })

    # Replacement for redacted values
    REDACTED_VALUE: str = "[REDACTED]"

# =============================================================================
# ENVIRONMENT VARIABLE NAMES - consistent prefix
# =============================================================================
class EnvVars:
    """Environment variable names."""
    PREFIX: str = "TIMETRACER_"

    MODE: str = "TIMETRACER_MODE"
    SERVICE: str = "TIMETRACER_SERVICE"
    ENV: str = "TIMETRACER_ENV"
    DIR: str = "TIMETRACER_DIR"
    CASSETTE: str = "TIMETRACER_CASSETTE"
    CAPTURE: str = "TIMETRACER_CAPTURE"
    SAMPLE_RATE: str = "TIMETRACER_SAMPLE_RATE"
    ERRORS_ONLY: str = "TIMETRACER_ERRORS_ONLY"
    EXCLUDE_PATHS: str = "TIMETRACER_EXCLUDE_PATHS"
    MAX_BODY_KB: str = "TIMETRACER_MAX_BODY_KB"
    STORE_REQ_BODY: str = "TIMETRACER_STORE_REQ_BODY"
    STORE_RES_BODY: str = "TIMETRACER_STORE_RES_BODY"
    STRICT_REPLAY: str = "TIMETRACER_STRICT_REPLAY"
    LOG_LEVEL: str = "TIMETRACER_LOG_LEVEL"
    MOCK_PLUGINS: str = "TIMETRACER_MOCK_PLUGINS"
    LIVE_PLUGINS: str = "TIMETRACER_LIVE_PLUGINS"

# =============================================================================
# ALLOWED HEADERS - headers we keep (allow-list approach for outbound)
# =============================================================================
ALLOWED_HEADERS: frozenset[str] = frozenset({
    "content-type",
    "content-length",
    "accept",
    "user-agent",
    "x-request-id",
    "x-correlation-id",
})
