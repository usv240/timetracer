"""
Capture policies for body data.

Controls when and how much body data is captured.
"""

from __future__ import annotations

from timetracer.constants import CapturePolicy


def should_store_body(
    policy: CapturePolicy | str,
    is_error: bool = False,
) -> bool:
    """
    Determine if body should be stored based on policy.

    Args:
        policy: The capture policy (never, on_error, always).
        is_error: Whether the request resulted in an error.

    Returns:
        True if body should be stored.
    """
    # Handle string policy
    if isinstance(policy, str):
        policy = CapturePolicy(policy.lower())

    if policy == CapturePolicy.ALWAYS:
        return True
    elif policy == CapturePolicy.NEVER:
        return False
    elif policy == CapturePolicy.ON_ERROR:
        return is_error

    return False


def truncate_body(
    data: bytes,
    max_kb: int,
) -> tuple[bytes, bool]:
    """
    Truncate body data if it exceeds size limit.

    Args:
        data: The body bytes.
        max_kb: Maximum size in kilobytes.

    Returns:
        Tuple of (truncated_data, was_truncated).
    """
    max_bytes = max_kb * 1024

    if len(data) <= max_bytes:
        return data, False

    return data[:max_bytes], True


def get_body_size_kb(data: bytes) -> float:
    """Get body size in kilobytes."""
    return len(data) / 1024
