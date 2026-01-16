"""
Hashing utilities for body matching.

Provides consistent hashing for signature comparison during replay.
"""

import hashlib
import json
from typing import Any


def hash_body(data: bytes | str | Any) -> str:
    """
    Create a stable hash of body data.

    Args:
        data: Body data as bytes, string, or JSON-serializable object.

    Returns:
        SHA-256 hash prefixed with "sha256:".
    """
    if data is None:
        return "sha256:none"

    # Convert to bytes
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    elif isinstance(data, bytes):
        data_bytes = data
    else:
        # JSON serialize for objects
        try:
            data_bytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            data_bytes = str(data).encode("utf-8")

    hash_value = hashlib.sha256(data_bytes).hexdigest()
    return f"sha256:{hash_value}"


def hash_string(value: str) -> str:
    """
    Create a hash of a string value.

    Args:
        value: String to hash.

    Returns:
        SHA-256 hash prefixed with "sha256:".
    """
    hash_value = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{hash_value}"


def short_hash(data: bytes | str | Any, length: int = 8) -> str:
    """
    Create a short hash for display purposes.

    Args:
        data: Data to hash.
        length: Number of characters to return.

    Returns:
        Truncated hash without prefix.
    """
    full_hash = hash_body(data)
    # Remove "sha256:" prefix and truncate
    return full_hash.split(":")[1][:length]
