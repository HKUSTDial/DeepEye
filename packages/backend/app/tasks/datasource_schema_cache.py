from __future__ import annotations

import copy
import hashlib
import json
import time
from collections import OrderedDict
from threading import RLock
from typing import Any

from app.core.config import settings

_cache: OrderedDict[str, tuple[float, list[dict[str, object]]]] = OrderedDict()
_lock = RLock()


def build_datasource_schema_cache_key(
    datasource: Any,
    *,
    max_tables: int,
    max_columns: int,
    preview_rows: int,
) -> str:
    payload = {
        "id": str(getattr(datasource, "id", "")),
        "name": getattr(datasource, "name", None),
        "type": getattr(datasource, "type", None),
        "category": getattr(datasource, "category", None),
        "connection_string": getattr(datasource, "connection_string", None),
        "storage_path": getattr(datasource, "storage_path", None),
        "file_metadata": getattr(datasource, "file_metadata", None),
        "max_tables": max_tables,
        "max_columns": max_columns,
        "preview_rows": preview_rows,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_cached_datasource_schema(cache_key: str) -> list[dict[str, object]] | None:
    now = time.time()
    with _lock:
        _prune_expired(now)
        entry = _cache.get(cache_key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            _cache.pop(cache_key, None)
            return None
        _cache.move_to_end(cache_key)
        return copy.deepcopy(value)


def set_cached_datasource_schema(cache_key: str, value: list[dict[str, object]]) -> None:
    now = time.time()
    expires_at = now + max(int(settings.AGENT_DATASOURCE_SCHEMA_CACHE_TTL_SECONDS), 1)
    with _lock:
        _prune_expired(now)
        _cache[cache_key] = (expires_at, copy.deepcopy(value))
        _cache.move_to_end(cache_key)
        max_entries = max(int(settings.AGENT_DATASOURCE_SCHEMA_CACHE_MAX_ENTRIES), 1)
        while len(_cache) > max_entries:
            _cache.popitem(last=False)


def clear_datasource_schema_cache() -> None:
    with _lock:
        _cache.clear()


def _prune_expired(now: float) -> None:
    expired_keys = [key for key, (expires_at, _) in _cache.items() if expires_at <= now]
    for key in expired_keys:
        _cache.pop(key, None)
