"""
Signature matching for replay.

Provides utilities for comparing recorded and actual call signatures.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from timetracer.types import EventSignature


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison.

    Removes query string, normalizes scheme/host/path.
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def normalize_query(query_string: str) -> dict[str, Any]:
    """Normalize query string to sorted dict."""
    parsed = parse_qs(query_string)
    # Flatten single-value lists
    return {k: v[0] if len(v) == 1 else sorted(v) for k, v in sorted(parsed.items())}


def signatures_match(
    expected: EventSignature,
    actual: dict[str, Any],
    *,
    check_body_hash: bool = False,
) -> tuple[bool, list[str]]:
    """
    Check if two signatures match.

    Args:
        expected: The recorded signature.
        actual: The actual call signature dict.
        check_body_hash: Whether to compare body hashes.

    Returns:
        Tuple of (matches, list of mismatch reasons).
    """
    mismatches: list[str] = []

    # Check method
    if expected.method != actual.get("method"):
        mismatches.append(
            f"method: expected {expected.method}, got {actual.get('method')}"
        )

    # Check URL
    expected_url = normalize_url(expected.url) if expected.url else None
    actual_url = normalize_url(actual.get("url", "")) if actual.get("url") else None

    if expected_url != actual_url:
        mismatches.append(
            f"url: expected {expected_url}, got {actual_url}"
        )

    # Check body hash (optional)
    if check_body_hash and expected.body_hash:
        if expected.body_hash != actual.get("body_hash"):
            mismatches.append(
                f"body_hash: expected {expected.body_hash[:20]}..., got {actual.get('body_hash', 'none')[:20]}..."
            )

    return len(mismatches) == 0, mismatches


def create_signature_summary(sig: EventSignature) -> str:
    """Create a human-readable summary of a signature."""
    parts = [sig.method]
    if sig.url:
        parts.append(sig.url)
    if sig.query:
        parts.append(f"?{len(sig.query)} params")
    return " ".join(parts)
