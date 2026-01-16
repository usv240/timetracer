"""
Context management for Timetracer.

Uses contextvars to provide async-safe, per-request session isolation.
This ensures concurrent requests don't mix their captured events.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from timetracer.session import BaseSession


# The central context variable holding the current session
# This is the ONLY place where session state is stored
_current_session: ContextVar[BaseSession | None] = ContextVar(
    "timetracer_current_session",
    default=None
)


def get_current_session() -> BaseSession | None:
    """
    Get the current trace session, if any.

    Returns None if no session is active (timetrace disabled or outside request).
    """
    return _current_session.get()


def set_session(session: BaseSession) -> Token[BaseSession | None]:
    """
    Set the current trace session.

    Returns a token that must be used to reset the session later.
    This pattern ensures proper cleanup even with exceptions.

    Usage:
        token = set_session(my_session)
        try:
            # ... do work ...
        finally:
            reset_session(token)
    """
    return _current_session.set(session)


def reset_session(token: Token[BaseSession | None]) -> None:
    """
    Reset the session to its previous value using the token.

    This should be called in a finally block to ensure cleanup.
    """
    _current_session.reset(token)


def clear_session() -> None:
    """
    Clear the current session (set to None).

    This is a convenience method; prefer reset_session(token) when possible.
    """
    _current_session.set(None)


def require_session() -> BaseSession:
    """
    Get the current session, raising if none exists.

    Use this in plugins that must have an active session.

    Raises:
        RuntimeError: If no session is active.
    """
    session = _current_session.get()
    if session is None:
        raise RuntimeError(
            "No active Timetracer session. "
            "Ensure you're inside a traced request and timetrace is enabled."
        )
    return session


def has_active_session() -> bool:
    """
    Check if there's an active trace session.

    Useful for plugins to decide whether to capture events.
    """
    return _current_session.get() is not None
