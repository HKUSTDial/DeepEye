"""Event Bus abstraction for real-time event publishing."""

from abc import ABC, abstractmethod

import redis.asyncio as aioredis


class EventBus(ABC):
    """Abstract async event bus for publishing events."""

    @abstractmethod
    async def publish(self, channel: str, data: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class RedisEventBus(EventBus):
    """Redis Pub/Sub implementation using async client."""

    def __init__(self, redis_url: str):
        self._client = aioredis.from_url(redis_url)

    async def publish(self, channel: str, data: str) -> None:
        await self._client.publish(channel, data)

    async def close(self) -> None:
        await self._client.aclose()

