"""Policies module for redaction and capture control."""

from timetracer.policies.capture import should_store_body, truncate_body
from timetracer.policies.redaction import (
    redact_body,
    redact_headers,
    redact_headers_allowlist,
)

__all__ = [
    "redact_headers",
    "redact_headers_allowlist",
    "redact_body",
    "should_store_body",
    "truncate_body",
]
