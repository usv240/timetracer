"""
Base plugin infrastructure.

Defines the plugin protocol and registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from timetracer.constants import EventType

if TYPE_CHECKING:
    from timetracer.config import TraceConfig


@runtime_checkable
class TracePlugin(Protocol):
    """
    Protocol for Timetracer plugins.

    Plugins must implement this interface to integrate with the system.
    """

    @property
    def name(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    def event_type(self) -> EventType:
        """The type of events this plugin captures."""
        ...

    def setup(self, config: TraceConfig) -> None:
        """Initialize the plugin with configuration."""
        ...

    def enable_recording(self) -> None:
        """Start capturing events."""
        ...

    def enable_replay(self) -> None:
        """Start mocking calls with recorded data."""
        ...

    def disable(self) -> None:
        """Stop capturing/mocking and restore original behavior."""
        ...


# Plugin registry
_registered_plugins: dict[str, TracePlugin] = {}


def register_plugin(plugin: TracePlugin) -> None:
    """Register a plugin globally."""
    _registered_plugins[plugin.name] = plugin


def get_plugin(name: str) -> TracePlugin | None:
    """Get a registered plugin by name."""
    return _registered_plugins.get(name)


def get_all_plugins() -> dict[str, TracePlugin]:
    """Get all registered plugins."""
    return _registered_plugins.copy()


def clear_plugins() -> None:
    """Clear all registered plugins (for testing)."""
    _registered_plugins.clear()
