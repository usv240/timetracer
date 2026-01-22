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
# COMPRESSION TYPE
# =============================================================================
class CompressionType(str, Enum):
    """Compression type for cassette files."""
    NONE = "none"
    GZIP = "gzip"

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
    COMPRESSION: CompressionType = CompressionType.NONE

# =============================================================================
# REDACTION CONSTANTS - headers to always remove
# =============================================================================
class Redaction:
    """Redaction rules for sensitive data protection."""

    # Headers that are ALWAYS removed (case-insensitive matching)
    SENSITIVE_HEADERS: frozenset[str] = frozenset({
        # Authentication
        "authorization",
        "x-api-key",
        "x-auth-token",
        "x-access-token",
        "x-refresh-token",
        "x-session-token",
        "x-csrf-token",
        "x-xsrf-token",
        # Session/Cookies
        "cookie",
        "set-cookie",
        # Proxy authentication
        "proxy-authorization",
        "www-authenticate",
        # API keys in headers
        "api-key",
        "apikey",
        "x-client-secret",
        "x-secret-key",
    })

    # Body keys that should be masked (case-insensitive SUBSTRING matching)
    # This means "user_password" will match because it contains "password"
    SENSITIVE_BODY_KEYS: frozenset[str] = frozenset({
        # =====================================================================
        # AUTHENTICATION & CREDENTIALS
        # =====================================================================
        "password",
        "passwd",
        "pwd",
        "secret",
        "auth_token",
        "auth_key",

        # =====================================================================
        # TOKENS & KEYS
        # =====================================================================
        "token",
        "api_key",
        "apikey",
        "api-key",
        "access_token",
        "refresh_token",
        "id_token",
        "session_token",
        "session_id",
        "sessionid",
        "bearer",
        "jwt",
        "oauth",
        "private_key",
        "privatekey",
        "public_key",
        "signing_key",
        "encryption_key",
        "secret_key",
        "secretkey",
        "client_secret",
        "client_id",  # Often paired with secrets

        # =====================================================================
        # SECURITY TOKENS
        # =====================================================================
        "csrf",
        "xsrf",
        "nonce",
        "otp",
        "totp",
        "hotp",
        "mfa",
        "2fa",
        "pin",
        "verification_code",
        "reset_token",
        "magic_link",

        # =====================================================================
        # PERSONAL IDENTIFIABLE INFORMATION (PII)
        # =====================================================================
        "ssn",
        "social_security",
        "national_id",
        "passport",
        "driver_license",
        "drivers_license",
        "tax_id",
        "taxpayer",

        # Contact info
        "phone",
        "mobile",
        "telephone",
        "fax",
        "email",
        "email_address",

        # Personal details
        "date_of_birth",
        "dob",
        "birth_date",
        "birthdate",
        "age",
        "gender",
        "sex",
        "race",
        "ethnicity",
        "religion",
        "nationality",

        # Address
        "address",
        "street",
        "zip_code",
        "zipcode",
        "postal_code",
        "postcode",

        # =====================================================================
        # FINANCIAL DATA (PCI-DSS)
        # =====================================================================
        "credit_card",
        "creditcard",
        "card_number",
        "cardnumber",
        "cc_number",
        "debit_card",
        "cvv",
        "cvc",
        "cvv2",
        "cvc2",
        "security_code",
        "expiry",
        "expiration",
        "exp_date",
        "exp_month",
        "exp_year",
        "cardholder",
        "bank_account",
        "account_number",
        "routing_number",
        "iban",
        "swift",
        "bic",
        "sort_code",

        # =====================================================================
        # HEALTHCARE (HIPAA)
        # =====================================================================
        "medical_record",
        "patient_id",
        "health_id",
        "diagnosis",
        "prescription",
        "treatment",
        "insurance_id",
        "member_id",
        "policy_number",
        "claim_number",
        "provider_id",
        "npi",  # National Provider Identifier

        # =====================================================================
        # OTHER SENSITIVE FIELDS
        # =====================================================================
        "signature",
        "biometric",
        "fingerprint",
        "face_id",
        "voice_print",
        "ip_address",
        "mac_address",
        "device_id",
        "imei",
        "serial_number",
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
    COMPRESSION: str = "TIMETRACER_COMPRESSION"

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
