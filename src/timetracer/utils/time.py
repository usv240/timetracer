"""
Time utilities for duration tracking.

Provides a Timer context manager for accurate timing.
"""

import time
from dataclasses import dataclass


@dataclass
class TimingResult:
    """Result of a timing operation."""
    start_ns: int
    end_ns: int

    @property
    def duration_ns(self) -> int:
        """Duration in nanoseconds."""
        return self.end_ns - self.start_ns

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1_000_000

    @property
    def duration_s(self) -> float:
        """Duration in seconds."""
        return self.duration_ns / 1_000_000_000


class Timer:
    """
    A timer for measuring operation duration.

    Can be used as a context manager or manually.

    Usage:
        # Context manager
        with Timer() as t:
            do_something()
        print(f"Took {t.duration_ms}ms")

        # Manual
        timer = Timer()
        timer.start()
        do_something()
        timer.stop()
        print(f"Took {timer.duration_ms}ms")
    """

    def __init__(self) -> None:
        self._start_ns: int | None = None
        self._end_ns: int | None = None

    def start(self) -> None:
        """Start the timer."""
        self._start_ns = time.perf_counter_ns()
        self._end_ns = None

    def stop(self) -> TimingResult:
        """Stop the timer and return result."""
        if self._start_ns is None:
            raise RuntimeError("Timer was not started")

        self._end_ns = time.perf_counter_ns()
        return TimingResult(self._start_ns, self._end_ns)

    @property
    def duration_ns(self) -> int:
        """Duration in nanoseconds (uses current time if not stopped)."""
        if self._start_ns is None:
            return 0
        end = self._end_ns if self._end_ns is not None else time.perf_counter_ns()
        return end - self._start_ns

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1_000_000

    @property
    def elapsed_ms(self) -> float:
        """Alias for duration_ms (more intuitive during ongoing timing)."""
        return self.duration_ms

    def __enter__(self) -> "Timer":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


def get_offset_ms(start_time: float) -> float:
    """
    Get milliseconds elapsed since a start time.

    Args:
        start_time: Start time from time.perf_counter().

    Returns:
        Milliseconds elapsed.
    """
    return (time.perf_counter() - start_time) * 1000
