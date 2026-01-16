"""Framework integrations for Timetrace."""

from timetrace.integrations.fastapi import TimeTraceMiddleware

# Flask is optional
try:
    from timetrace.integrations.flask import TimeTraceMiddleware as FlaskMiddleware
    from timetrace.integrations.flask import init_app
    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False
    FlaskMiddleware = None
    init_app = None

__all__ = ["TimeTraceMiddleware", "FlaskMiddleware", "init_app"]
