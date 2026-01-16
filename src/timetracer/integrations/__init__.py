"""Framework integrations for Timetracer."""

from timetracer.integrations.fastapi import timetracerMiddleware

# Flask is optional
try:
    from timetracer.integrations.flask import init_app
    from timetracer.integrations.flask import timetracerMiddleware as FlaskMiddleware
    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False
    FlaskMiddleware = None
    init_app = None

__all__ = ["timetracerMiddleware", "FlaskMiddleware", "init_app"]
