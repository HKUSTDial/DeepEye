from typing import Any, Dict, List, Optional
from uuid import UUID
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from app.api.schemas import AgentEvent, AgentEventType
import redis.asyncio as redis
import asyncio

class RedisStreamingCallback(BaseCallbackHandler):
    """
    Callback handler that publishes LangChain events to Redis Pub/Sub.
    Used for Sub-Agents running inside Tools to stream their internal steps.
    """
    def __init__(self, redis_client: redis.Redis, channel: str, source: str, ignore_tags: List[str] = None):
        self.redis_client = redis_client
        self.channel = channel
        self.source = source
        self.ignore_tags = set(ignore_tags or [])
        # Loop capture is risky if cross-thread, better to rely on async execution context

    def _should_ignore(self, kwargs: Dict[str, Any]) -> bool:
        tags = kwargs.get("tags") or []
        return any(tag in self.ignore_tags for tag in tags)

    async def _publish(self, event: AgentEvent):
        """Helper to publish async"""
        await self.redis_client.publish(self.channel, event.model_dump_json())

    async def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any) -> Any:
        pass # Optional: indicate thinking start

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        """Stream tokens"""
        if self._should_ignore(kwargs): return
        
        if token:
            event = AgentEvent(
                type=AgentEventType.TOKEN,
                source=self.source,
                content=token
            )
            await self._publish(event)

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        if self._should_ignore(kwargs): return
        
        event = AgentEvent(
            type=AgentEventType.TOOL_START,
            source=self.source, # e.g. "sql_agent"
            data={"name": serialized.get("name"), "input": input_str}
        )
        await self._publish(event)

    async def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        if self._should_ignore(kwargs): return

        event = AgentEvent(
            type=AgentEventType.TOOL_END,
            source=self.source,
            data={"output": output}
        )
        await self._publish(event)

