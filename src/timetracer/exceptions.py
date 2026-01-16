"""
Centralized exceptions for Timetracer.

All custom exceptions are defined here to ensure consistent error handling.
"""

from typing import Any


class TimetracerError(Exception):
    """Base exception for all Timetracer errors."""
    pass


class CassetteError(TimetracerError):
    """Base exception for cassette-related errors."""
    pass


class CassetteNotFoundError(CassetteError):
    """Raised when a cassette file cannot be found."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Cassette not found: {path}")


class CassetteSchemaError(CassetteError):
    """Raised when a cassette has an invalid or incompatible schema."""

    def __init__(self, path: str, expected_version: str, actual_version: str | None):
        self.path = path
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Cassette schema mismatch in {path}: "
            f"expected {expected_version}, got {actual_version}"
        )


class ReplayMismatchError(TimetracerError):
    """
    Raised when a dependency call during replay doesn't match the recorded cassette.

    This provides detailed information to help debug what changed.
    """

    def __init__(
        self,
        message: str,
        *,
        cassette_path: str | None = None,
        endpoint: str | None = None,
        event_index: int | None = None,
        expected: dict[str, Any] | None = None,
        actual: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        self.cassette_path = cassette_path
        self.endpoint = endpoint
        self.event_index = event_index
        self.expected = expected or {}
        self.actual = actual or {}
        self.hint = hint

        # Build detailed error message
        lines = [message, ""]

        if cassette_path:
            lines.append(f"cassette: {cassette_path}")
        if endpoint:
            lines.append(f"endpoint: {endpoint}")
        if event_index is not None:
            lines.append(f"event index: #{event_index}")

        if expected:
            lines.append("")
            lines.append("expected:")
            for key, value in expected.items():
                lines.append(f"  {key}: {value}")

        if actual:
            lines.append("")
            lines.append("actual:")
            for key, value in actual.items():
                lines.append(f"  {key}: {value}")

        if hint:
            lines.append("")
            lines.append(f"hint: {hint}")

        super().__init__("\n".join(lines))


class ConfigurationError(TimetracerError):
    """Raised when there's an invalid configuration."""
    pass


class PluginError(TimetracerError):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not available."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(
            f"Plugin '{plugin_name}' not found. "
            f"Make sure it's installed: pip install timetracer[{plugin_name}]"
        )
