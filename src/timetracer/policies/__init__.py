"""Policies module for redaction and capture control."""

from timetracer.policies.capture import should_store_body, truncate_body
from timetracer.policies.redaction import (
    detect_pii,
    redact_body,
    redact_headers,
    redact_headers_allowlist,
    redact_pii_in_text,
)

__all__ = [
    "redact_headers",
    "redact_headers_allowlist",
    "redact_body",
    "detect_pii",
    "redact_pii_in_text",
    "should_store_body",
    "truncate_body",
]
