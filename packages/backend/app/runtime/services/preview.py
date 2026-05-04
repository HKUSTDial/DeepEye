from __future__ import annotations

import time
from datetime import datetime
from typing import Any


def preview_container_labels(*, preview_kind: str, task_id: str, session_id: str | None = None) -> dict[str, str]:
    labels = {
        "app": "deepeye",
        "component": "preview-runtime",
        "preview_kind": preview_kind,
        "task_id": task_id,
        "created_at_epoch": str(int(time.time())),
    }
    if session_id:
        labels["session_id"] = session_id
    return labels


def preview_containers_to_cleanup(
    containers: list[Any],
    *,
    now: float | None = None,
    ttl_seconds: int,
    max_running: int,
) -> list[Any]:
    if not containers:
        return []

    now = now if now is not None else time.time()
    max_running = max(max_running, 1)
    expired_or_stopped: list[Any] = []
    running: list[tuple[float, Any]] = []

    for container in containers:
        status = getattr(container, "status", "") or ""
        created_at = _container_created_at_epoch(container)
        is_expired = ttl_seconds > 0 and created_at > 0 and (now - created_at) > ttl_seconds

        if status != "running" or is_expired:
            expired_or_stopped.append(container)
            continue

        running.append((created_at, container))

    running.sort(key=lambda item: item[0], reverse=True)
    overflow = [container for _, container in running[max_running:]]

    seen: set[str] = set()
    result: list[Any] = []
    for container in [*expired_or_stopped, *overflow]:
        key = getattr(container, "name", None) or str(id(container))
        if key in seen:
            continue
        seen.add(key)
        result.append(container)
    return result


def _container_created_at_epoch(container: Any) -> float:
    labels = getattr(container, "labels", None) or {}
    labeled = labels.get("created_at_epoch")
    if isinstance(labeled, str):
        try:
            return float(labeled)
        except ValueError:
            pass

    created = ((getattr(container, "attrs", None) or {}).get("Created"))
    if isinstance(created, str):
        try:
            return datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0
    return 0
