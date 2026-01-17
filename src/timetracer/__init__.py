"""
Timetracer - Time-travel debugging for FastAPI and Flask

Record API requests into portable cassettes and replay them
with mocked dependencies for deterministic debugging.
"""

from timetracer.config import TraceConfig
from timetracer.constants import CapturePolicy, TraceMode
from timetracer.exceptions import (
    CassetteError,
    CassetteNotFoundError,
    CassetteSchemaError,
    ReplayMismatchError,
    TimetracerError,
)

__version__ = "1.1.0"
__all__ = [
    "__version__",
    "TraceConfig",
    "TraceMode",
    "CapturePolicy",
    "TimetracerError",
    "ReplayMismatchError",
    "CassetteError",
    "CassetteNotFoundError",
    "CassetteSchemaError",
]
