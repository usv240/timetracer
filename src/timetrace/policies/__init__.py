"""Policies module for redaction and capture control."""

from timetrace.policies.capture import should_store_body, truncate_body
from timetrace.policies.redaction import (
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
