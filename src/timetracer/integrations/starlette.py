"""
Starlette middleware for Timetracer.

Starlette is the lightweight ASGI foundation that FastAPI is built on.
Since both use the same ASGI interface, we can reuse the FastAPI middleware.

This module provides a thin wrapper and convenience functions for Starlette users.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from timetracer.config import TraceConfig

# Import the ASGI middleware from FastAPI (works for any ASGI app)
from timetracer.integrations.fastapi import TimeTracerMiddleware

if TYPE_CHECKING:
    from starlette.applications import Starlette


def auto_setup(
    app: Starlette,
    config: TraceConfig | None = None,
    plugins: list[str] | None = None,
) -> Starlette:
    """
    One-line Timetracer setup for Starlette.

    Adds middleware and enables plugins automatically.

    Args:
        app: Starlette application instance.
        config: Optional TraceConfig. If None, loads from environment.
        plugins: List of plugins to enable. Default: ["httpx"].
                 Options: "httpx", "requests", "sqlalchemy", "redis", "aiohttp"

    Returns:
        The app instance (for chaining).

    Usage:
        from starlette.applications import Starlette
        from timetracer.integrations.starlette import auto_setup

        app = auto_setup(Starlette(debug=True))

        # Or with options:
        app = Starlette()
        auto_setup(app, plugins=["httpx", "redis"])
    """
    cfg = config or TraceConfig.from_env()

    # Add middleware
    app.add_middleware(TimeTracerMiddleware, config=cfg)

    # Enable plugins
    enabled_plugins = plugins or ["httpx"]

    for plugin in enabled_plugins:
        if plugin == "httpx":
            from timetracer.plugins import enable_httpx
            enable_httpx()
        elif plugin == "requests":
            from timetracer.plugins import enable_requests
            enable_requests()
        elif plugin == "sqlalchemy":
            from timetracer.plugins import enable_sqlalchemy
            enable_sqlalchemy()
        elif plugin == "redis":
            from timetracer.plugins import enable_redis
            enable_redis()
        elif plugin == "aiohttp":
            from timetracer.plugins import enable_aiohttp
            enable_aiohttp()

    return app


# Backwards compatibility aliases
timetracerMiddleware = TimeTracerMiddleware

__all__ = [
    "TimeTracerMiddleware",
    "timetracerMiddleware",
    "auto_setup",
]
