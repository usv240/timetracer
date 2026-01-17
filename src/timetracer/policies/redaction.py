"""
Redaction policies for sensitive data.

Removes or masks sensitive headers and body content before storage.
Uses centralized constants for consistency.
"""

from __future__ import annotations

import re
from typing import Any

from timetracer.constants import ALLOWED_HEADERS, Redaction


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


# =============================================================================
# PII PATTERN DETECTION
# =============================================================================

# Compiled regex patterns for performance
_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    # Email addresses
    "email": re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE
    ),
    # Phone numbers (various formats)
    "phone": re.compile(
        r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    ),
    # US Social Security Numbers
    "ssn": re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    ),
    # Credit card numbers (with optional separators)
    "credit_card": re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    ),
    # IPv4 addresses
    "ipv4": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
    # IPv6 addresses (simplified)
    "ipv6": re.compile(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    ),
}


def _luhn_check(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.

    This helps distinguish actual credit card numbers from random 16-digit strings.
    """
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    # Luhn algorithm
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def detect_pii(value: str) -> str | None:
    """
    Detect PII patterns in a string value.

    Args:
        value: The string to check for PII patterns.

    Returns:
        The type of PII detected (e.g., 'email', 'phone', 'ssn', 'credit_card'),
        or None if no PII is detected.
    """
    if not isinstance(value, str) or len(value) < 5:
        return None

    # Check for email
    if _PII_PATTERNS["email"].search(value):
        return "email"

    # Check for SSN
    if _PII_PATTERNS["ssn"].fullmatch(value.replace("-", "").replace(" ", "")):
        return "ssn"

    # Check for credit card (with Luhn validation)
    cc_match = _PII_PATTERNS["credit_card"].search(value)
    if cc_match:
        cc_digits = "".join(c for c in cc_match.group() if c.isdigit())
        if _luhn_check(cc_digits):
            return "credit_card"

    # Check for phone
    if _PII_PATTERNS["phone"].search(value):
        # Avoid false positives - must have reasonable length
        digits_only = "".join(c for c in value if c.isdigit())
        if 10 <= len(digits_only) <= 15:
            return "phone"

    # Check for IP addresses
    if _PII_PATTERNS["ipv4"].search(value):
        return "ipv4"
    if _PII_PATTERNS["ipv6"].search(value):
        return "ipv6"

    return None


def _mask_token_like(value: str) -> str:
    """
    Mask token-like strings and PII patterns in values.

    Patterns detected:
    - JWT tokens (eyJ...)
    - Bearer tokens
    - API keys (long alphanumeric strings)
    - Email addresses
    - Credit card numbers (Luhn validated)
    - Social Security Numbers
    - Phone numbers
    - IP addresses
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

    # PII pattern detection
    pii_type = detect_pii(value)
    if pii_type:
        return f"[REDACTED:{pii_type.upper()}]"

    return value


def redact_pii_in_text(text: str) -> str:
    """
    Redact all detected PII patterns in a text string.

    This is useful for redacting PII in unstructured text fields
    like comments or descriptions.

    Args:
        text: The text to scan and redact.

    Returns:
        Text with PII patterns replaced with [REDACTED:TYPE].
    """
    if not isinstance(text, str):
        return text

    result = text

    # Redact emails
    result = _PII_PATTERNS["email"].sub("[REDACTED:EMAIL]", result)

    # Redact SSNs
    result = _PII_PATTERNS["ssn"].sub("[REDACTED:SSN]", result)

    # Redact credit cards (only those passing Luhn check)
    def replace_cc(match: re.Match[str]) -> str:
        cc_digits = "".join(c for c in match.group() if c.isdigit())
        if _luhn_check(cc_digits):
            return "[REDACTED:CREDIT_CARD]"
        return match.group()

    result = _PII_PATTERNS["credit_card"].sub(replace_cc, result)

    # Redact phone numbers
    def replace_phone(match: re.Match[str]) -> str:
        digits_only = "".join(c for c in match.group() if c.isdigit())
        if 10 <= len(digits_only) <= 15:
            return "[REDACTED:PHONE]"
        return match.group()

    result = _PII_PATTERNS["phone"].sub(replace_phone, result)

    # Redact IP addresses
    result = _PII_PATTERNS["ipv4"].sub("[REDACTED:IP]", result)
    result = _PII_PATTERNS["ipv6"].sub("[REDACTED:IP]", result)

    return result
