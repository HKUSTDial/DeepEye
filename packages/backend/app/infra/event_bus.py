"""Event Bus abstraction for real-time event publishing."""

from abc import ABC, abstractmethod

import redis


class EventBus(ABC):
    """Abstract event bus for publishing events."""

    @abstractmethod
    def publish(self, channel: str, data: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class RedisEventBus(EventBus):
    """Redis Pub/Sub implementation using sync client (avoids event loop issues in Celery)."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def publish(self, channel: str, data: str) -> None:
        self.client.publish(channel, data)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

