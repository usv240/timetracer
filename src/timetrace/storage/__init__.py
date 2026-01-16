"""
Storage backends for Timetrace cassettes.

Provides pluggable storage options:
- Local filesystem (default)
- S3 (AWS, MinIO, etc.)
"""

# S3 is optional
try:
    from timetrace.storage.s3 import S3Config, S3Store
    _HAS_S3 = True
except ImportError:
    _HAS_S3 = False
    S3Store = None  # type: ignore
    S3Config = None  # type: ignore

__all__ = ["S3Store", "S3Config"]
