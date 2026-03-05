"""Best-effort in-process login throttling."""

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

_FAILED_ATTEMPTS: dict[str, deque[float]] = {}
_LOCK = Lock()


def _prune(attempts: deque[float], now_ts: float, window_seconds: int) -> None:
    cutoff = now_ts - window_seconds
    while attempts and attempts[0] < cutoff:
        attempts.popleft()


def is_limited(key: str, *, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Check whether key exceeds attempt threshold."""
    now_ts = monotonic()
    with _LOCK:
        attempts = _FAILED_ATTEMPTS.get(key)
        if not attempts:
            return False, 0
        _prune(attempts, now_ts, window_seconds)
        if len(attempts) < max_attempts:
            if not attempts:
                _FAILED_ATTEMPTS.pop(key, None)
            return False, 0
        retry_after = max(1, ceil(window_seconds - (now_ts - attempts[0])))
        return True, retry_after


def record_failure(key: str, *, window_seconds: int) -> None:
    """Record a failed login attempt for key."""
    now_ts = monotonic()
    with _LOCK:
        attempts = _FAILED_ATTEMPTS.setdefault(key, deque())
        _prune(attempts, now_ts, window_seconds)
        attempts.append(now_ts)


def clear_failures(key: str) -> None:
    """Clear failed attempts for key."""
    with _LOCK:
        _FAILED_ATTEMPTS.pop(key, None)
