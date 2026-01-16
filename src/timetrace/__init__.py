"""
Timetrace - Time-travel debugging for FastAPI and Flask

Record API requests into portable cassettes and replay them
with mocked dependencies for deterministic debugging.
"""

from timetrace.config import TraceConfig
from timetrace.constants import CapturePolicy, TraceMode
from timetrace.exceptions import (
    CassetteError,
    CassetteNotFoundError,
    CassetteSchemaError,
    ReplayMismatchError,
    TimetraceError,
)

__version__ = "1.0.0"
__all__ = [
    "__version__",
    "TraceConfig",
    "TraceMode",
    "CapturePolicy",
    "TimetraceError",
    "ReplayMismatchError",
    "CassetteError",
    "CassetteNotFoundError",
    "CassetteSchemaError",
]
