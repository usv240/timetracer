"""Framework integrations for Timetracer."""

from timetracer.integrations.fastapi import TimeTraceMiddleware, TimeTracerMiddleware, auto_setup

# Alias for backwards compatibility
timetracerMiddleware = TimeTracerMiddleware

# Flask is optional
try:
    from timetracer.integrations.flask import TimeTracerMiddleware as FlaskMiddleware
    from timetracer.integrations.flask import auto_setup as flask_auto_setup
    from timetracer.integrations.flask import init_app
    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False
    FlaskMiddleware = None
    init_app = None
    flask_auto_setup = None

__all__ = [
    "TimeTracerMiddleware",
    "TimeTraceMiddleware",  # Deprecated alias
    "timetracerMiddleware",  # Alias
    "auto_setup",
    "FlaskMiddleware",
    "init_app",
    "flask_auto_setup",
]

