"""Framework integrations for Timetracer."""

from timetracer.integrations.fastapi import (
    TimeTraceMiddleware,
    TimeTracerMiddleware,
    auto_setup,
)

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

# Django is optional
try:
    from timetracer.integrations.django import TimeTracerMiddleware as DjangoMiddleware
    from timetracer.integrations.django import auto_setup as django_auto_setup
    _HAS_DJANGO = True
except ImportError:
    _HAS_DJANGO = False
    DjangoMiddleware = None
    django_auto_setup = None

# Starlette is optional (but shares FastAPI's middleware)
try:
    from timetracer.integrations.starlette import TimeTracerMiddleware as StarletteMiddleware
    from timetracer.integrations.starlette import auto_setup as starlette_auto_setup
    _HAS_STARLETTE = True
except ImportError:
    _HAS_STARLETTE = False
    StarletteMiddleware = None
    starlette_auto_setup = None

__all__ = [
    "TimeTracerMiddleware",
    "TimeTraceMiddleware",  # Deprecated alias
    "timetracerMiddleware",  # Alias
    "auto_setup",
    "FlaskMiddleware",
    "init_app",
    "flask_auto_setup",
    "DjangoMiddleware",
    "django_auto_setup",
    "StarletteMiddleware",
    "starlette_auto_setup",
]


