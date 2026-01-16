"""
Plugins module for Timetrace.

Plugins capture and replay dependency calls (HTTP, DB, Redis, etc.).
"""

from timetrace.plugins.httpx_plugin import disable_httpx, enable_httpx
from timetrace.plugins.requests_plugin import disable_requests, enable_requests

# SQLAlchemy is optional - only import if available
try:
    from timetrace.plugins.sqlalchemy_plugin import disable_sqlalchemy, enable_sqlalchemy
    _HAS_SQLALCHEMY = True
except ImportError:
    _HAS_SQLALCHEMY = False

    def enable_sqlalchemy(*args, **kwargs):
        raise ImportError("sqlalchemy is required. Install with: pip install timetrace[sqlalchemy]")

    def disable_sqlalchemy(*args, **kwargs):
        pass

# Redis is optional - only import if available
try:
    from timetrace.plugins.redis_plugin import disable_redis, enable_redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

    def enable_redis(*args, **kwargs):
        raise ImportError("redis is required. Install with: pip install timetrace[redis]")

    def disable_redis(*args, **kwargs):
        pass

__all__ = [
    "enable_httpx", "disable_httpx",
    "enable_requests", "disable_requests",
    "enable_sqlalchemy", "disable_sqlalchemy",
    "enable_redis", "disable_redis",
]

