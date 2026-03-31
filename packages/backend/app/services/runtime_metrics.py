from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any


def _metric_key(name: str, tags: dict[str, Any] | None = None) -> str:
    if not tags:
        return name
    serialized = ",".join(f"{key}={tags[key]}" for key in sorted(tags))
    return f"{name}[{serialized}]"


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._timings: dict[str, dict[str, float | None]] = {}

    def increment(self, name: str, amount: float = 1, *, tags: dict[str, Any] | None = None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._counters[key] += amount

    def set_gauge(self, name: str, value: float, *, tags: dict[str, Any] | None = None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._gauges[key] = value

    def change_gauge(self, name: str, delta: float, *, tags: dict[str, Any] | None = None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._gauges[key] += delta

    def record_duration(self, name: str, seconds: float, *, tags: dict[str, Any] | None = None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            current = self._timings.get(
                key,
                {
                    "count": 0.0,
                    "total_seconds": 0.0,
                    "min_seconds": None,
                    "max_seconds": None,
                    "last_seconds": None,
                },
            )
            current["count"] = float(current["count"] or 0) + 1
            current["total_seconds"] = float(current["total_seconds"] or 0.0) + seconds
            current["last_seconds"] = seconds
            min_seconds = current["min_seconds"]
            max_seconds = current["max_seconds"]
            current["min_seconds"] = seconds if min_seconds is None else min(min_seconds, seconds)
            current["max_seconds"] = seconds if max_seconds is None else max(max_seconds, seconds)
            self._timings[key] = current

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timings: dict[str, dict[str, float | None]] = {}
            for key, value in self._timings.items():
                count = float(value["count"] or 0)
                total = float(value["total_seconds"] or 0.0)
                timings[key] = {
                    **value,
                    "avg_seconds": (total / count) if count else None,
                }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": timings,
            }


runtime_metrics = RuntimeMetrics()
