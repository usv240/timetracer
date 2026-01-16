"""
Redaction policies for sensitive data.

Removes or masks sensitive headers and body content before storage.
Uses centralized constants for consistency.
"""

from __future__ import annotations

import re
from typing import Any

from timetrace.constants import ALLOWED_HEADERS, Redaction


def redact_headers(
    headers: dict[str, str],
    *,
    mode: str = "drop",
    additional_sensitive: set[str] | None = None,
) -> dict[str, str]:
    """
    Redact sensitive headers.

    Args:
        headers: Original headers dict.
        mode: "drop" to remove sensitive headers, "mask" to replace values.
        additional_sensitive: Additional header names to treat as sensitive.

    Returns:
        New dict with sensitive headers removed or masked.
    """
    sensitive = Redaction.SENSITIVE_HEADERS
    if additional_sensitive:
        sensitive = sensitive | {h.lower() for h in additional_sensitive}

    result = {}
    for key, value in headers.items():
        key_lower = key.lower()

        if key_lower in sensitive:
            if mode == "mask":
                result[key] = Redaction.REDACTED_VALUE
            # else: drop (don't include)
        else:
            result[key] = value

    return result


def redact_headers_allowlist(
    headers: dict[str, str],
    allowed: frozenset[str] | None = None,
) -> dict[str, str]:
    """
    Keep only allowed headers (allowlist approach).

    This is safer than blocklist - only explicitly allowed headers are kept.

    Args:
        headers: Original headers dict.
        allowed: Set of allowed header names (lowercase). Defaults to ALLOWED_HEADERS.

    Returns:
        New dict with only allowed headers.
    """
    if allowed is None:
        allowed = ALLOWED_HEADERS

    return {
        key: value
        for key, value in headers.items()
        if key.lower() in allowed
    }


def redact_body(
    body: Any,
    *,
    additional_sensitive_keys: set[str] | None = None,
) -> Any:
    """
    Redact sensitive keys in a body object.

    Recursively processes dicts and lists.

    Args:
        body: The body data (usually a dict or list).
        additional_sensitive_keys: Additional keys to redact.

    Returns:
        New object with sensitive values masked.
    """
    if body is None:
        return None

    sensitive_keys = Redaction.SENSITIVE_BODY_KEYS
    if additional_sensitive_keys:
        sensitive_keys = sensitive_keys | {k.lower() for k in additional_sensitive_keys}

    return _redact_recursive(body, sensitive_keys)


def _redact_recursive(obj: Any, sensitive_keys: frozenset[str]) -> Any:
    """Recursively redact sensitive keys."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if _is_sensitive_key(key, sensitive_keys):
                result[key] = Redaction.REDACTED_VALUE
            else:
                result[key] = _redact_recursive(value, sensitive_keys)
        return result

    elif isinstance(obj, list):
        return [_redact_recursive(item, sensitive_keys) for item in obj]

    elif isinstance(obj, str):
        # Optionally mask token-like strings
        return _mask_token_like(obj)

    else:
        return obj


def _is_sensitive_key(key: str, sensitive_keys: frozenset[str]) -> bool:
    """Check if a key is sensitive (case-insensitive substring match)."""
    key_lower = key.lower()

    # Exact match
    if key_lower in sensitive_keys:
        return True

    # Substring match for compound keys
    for sensitive in sensitive_keys:
        if sensitive in key_lower:
            return True

    return False


def _mask_token_like(value: str) -> str:
    """
    Mask token-like strings in values.

    Patterns:
    - JWT tokens (eyJ...)
    - Bearer tokens
    - API keys (long alphanumeric strings)
    """
    # JWT pattern
    if value.startswith("eyJ") and value.count(".") == 2:
        return Redaction.REDACTED_VALUE

    # Bearer prefix
    if value.lower().startswith("bearer "):
        return f"Bearer {Redaction.REDACTED_VALUE}"

    # Very long alphanumeric strings (likely API keys)
    if len(value) > 32 and re.match(r"^[a-zA-Z0-9_-]+$", value):
        # Only mask if it looks random (has mixed case or underscores)
        if re.search(r"[a-z]", value) and re.search(r"[A-Z0-9_-]", value):
            return Redaction.REDACTED_VALUE

    return value
