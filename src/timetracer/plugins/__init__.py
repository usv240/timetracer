"""
Plugins module for Timetracer.

Plugins capture and replay dependency calls (HTTP, DB, Redis, etc.).
"""

from timetracer.plugins.httpx_plugin import disable_httpx, enable_httpx
from timetracer.plugins.requests_plugin import disable_requests, enable_requests

# aiohttp is optional - only import if available
try:
    from timetracer.plugins.aiohttp_plugin import disable_aiohttp, enable_aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

    def enable_aiohttp(*args, **kwargs):
        raise ImportError("aiohttp is required. Install with: pip install timetracer[aiohttp]")

    def disable_aiohttp(*args, **kwargs):
        pass

# SQLAlchemy is optional - only import if available
try:
    from timetracer.plugins.sqlalchemy_plugin import disable_sqlalchemy, enable_sqlalchemy
    _HAS_SQLALCHEMY = True
except ImportError:
    _HAS_SQLALCHEMY = False

    def enable_sqlalchemy(*args, **kwargs):
        raise ImportError("sqlalchemy is required. Install with: pip install timetracer[sqlalchemy]")

    def disable_sqlalchemy(*args, **kwargs):
        pass

# Redis is optional - only import if available
try:
    from timetracer.plugins.redis_plugin import disable_redis, enable_redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

    def enable_redis(*args, **kwargs):
        raise ImportError("redis is required. Install with: pip install timetracer[redis]")

    def disable_redis(*args, **kwargs):
        pass

__all__ = [
    "enable_httpx", "disable_httpx",
    "enable_requests", "disable_requests",
    "enable_aiohttp", "disable_aiohttp",
    "enable_sqlalchemy", "disable_sqlalchemy",
    "enable_redis", "disable_redis",
]


