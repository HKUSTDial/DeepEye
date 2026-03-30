"""Activity tracking for sandbox lifecycle management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import redis

from deepeye.utils.logger import logger
from app.core.config import settings

_ACTIVITY_KEY_PREFIX = "deepeye:sandbox:activity"
_REDIS_RETRY_COOLDOWN_SECONDS = 5
_REDIS_SOCKET_TIMEOUT_SECONDS = 0.25


class ActivityTracker:
    """
    Track sandbox activity for idle detection.

    Activity is kept in a local in-memory cache for the current process and
    mirrored to Redis so that API and worker processes observe the same
    last-active timestamps during cleanup.
    """

    def __init__(
        self,
        *,
        redis_client: redis.Redis | None = None,
        redis_key_prefix: str = _ACTIVITY_KEY_PREFIX,
    ) -> None:
        self._activities: Dict[str, datetime] = {}
        self._redis = redis_client
        self._redis_key_prefix = redis_key_prefix
        self._redis_disabled_until: datetime | None = None

    def record_activity(self, session_id: str, *, at: datetime | None = None) -> None:
        """Record activity for a session in local cache and Redis."""
        last_active = at or datetime.utcnow()
        self._activities[session_id] = last_active
        self._store_remote_last_active(session_id, last_active)

    def get_last_active(self, session_id: str) -> datetime | None:
        """Get last active time from the freshest local/remote source."""
        last_active = self._activities.get(session_id)
        remote_last_active = self._load_remote_last_active(session_id)
        if remote_last_active and (last_active is None or remote_last_active > last_active):
            self._activities[session_id] = remote_last_active
            return remote_last_active
        return last_active

    def get_idle_time(self, session_id: str) -> timedelta:
        """Get time since last activity, or ``timedelta.max`` if unknown."""
        last_active = self.get_last_active(session_id)
        if not last_active:
            return timedelta.max
        return datetime.utcnow() - last_active

    def is_idle(self, session_id: str, timeout_seconds: int) -> bool:
        """Check whether a session has been idle longer than ``timeout_seconds``."""
        idle_time = self.get_idle_time(session_id)
        return idle_time.total_seconds() > timeout_seconds

    def should_stop(self, session_id: str, stop_timeout: int) -> bool:
        """Check whether a session should be stopped or destroyed."""
        return self.is_idle(session_id, stop_timeout)

    def clear(self, session_id: str) -> None:
        """Clear local and remote activity records for a session."""
        self._activities.pop(session_id, None)
        client = self._get_redis_client()
        if client is None:
            return
        try:
            client.delete(self._redis_key(session_id))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._handle_redis_failure("clear activity", exc)

    def get_all_sessions(self) -> list[str]:
        """Get all tracked session IDs from local cache and Redis."""
        session_ids = set(self._activities.keys())
        client = self._get_redis_client()
        if client is None:
            return sorted(session_ids)
        try:
            for key in client.scan_iter(match=f"{self._redis_key_prefix}:*"):
                session_ids.add(self._session_id_from_key(key))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._handle_redis_failure("list tracked sessions", exc)
        return sorted(session_ids)

    def get_stats(self) -> dict:
        """Get activity statistics."""
        session_ids = self.get_all_sessions()
        if not session_ids:
            return {
                "total_sessions": 0,
                "average_idle_seconds": 0,
            }

        idle_times = [
            self.get_idle_time(session_id).total_seconds()
            for session_id in session_ids
        ]
        return {
            "total_sessions": len(session_ids),
            "average_idle_seconds": sum(idle_times) / len(idle_times),
        }

    def _store_remote_last_active(self, session_id: str, last_active: datetime) -> None:
        client = self._get_redis_client()
        if client is None:
            return
        try:
            client.setex(
                self._redis_key(session_id),
                self._redis_ttl_seconds,
                last_active.isoformat(),
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._handle_redis_failure("record activity", exc)

    def _load_remote_last_active(self, session_id: str) -> datetime | None:
        client = self._get_redis_client()
        if client is None:
            return None
        try:
            payload = client.get(self._redis_key(session_id))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._handle_redis_failure("load activity", exc)
            return None
        return self._parse_datetime(payload)

    def _get_redis_client(self) -> redis.Redis | None:
        if self._redis is not None:
            return self._redis
        if self._redis_disabled_until and datetime.utcnow() < self._redis_disabled_until:
            return None
        try:
            self._redis = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=_REDIS_SOCKET_TIMEOUT_SECONDS,
                socket_timeout=_REDIS_SOCKET_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._handle_redis_failure("initialize Redis activity tracker", exc)
            return None
        return self._redis

    def _handle_redis_failure(self, action: str, exc: Exception) -> None:
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass
        self._redis = None
        self._redis_disabled_until = datetime.utcnow() + timedelta(seconds=_REDIS_RETRY_COOLDOWN_SECONDS)
        logger.warning("[ActivityTracker] Failed to %s via Redis, falling back to local state: %s", action, exc)

    @property
    def _redis_ttl_seconds(self) -> int:
        return max(
            settings.SANDBOX_DESTROY_TIMEOUT + settings.SANDBOX_CLEANUP_INTERVAL * 2,
            settings.SANDBOX_DESTROY_TIMEOUT,
        )

    def _redis_key(self, session_id: str) -> str:
        return f"{self._redis_key_prefix}:{session_id}"

    @staticmethod
    def _session_id_from_key(key: str | bytes) -> str:
        value = key.decode("utf-8") if isinstance(key, bytes) else key
        return value.rsplit(":", 1)[-1]

    @staticmethod
    def _parse_datetime(payload: str | bytes | None) -> datetime | None:
        if payload is None:
            return None
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
