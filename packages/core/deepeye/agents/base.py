from abc import ABC, abstractmethod
from typing import List, Any, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

class BaseAgent(ABC):
    """
    Abstract base class for all DeepEye agents.
    Defines the common interface that all agents must implement.
    """

    def __init__(
        self,
        model: BaseChatModel,
        tools: List[Any] | None = None,
        system_prompt: str = "",
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.model = model
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> Any:
        """Build and return the compiled LangGraph workflow."""
        ...

    @abstractmethod
    async def ainvoke(
        self, input_message: str, thread_id: str | None = None, config: dict | None = None
    ) -> dict:
        """Run the agent with a single input message."""
        ...

    @abstractmethod
    async def astream(
        self, input_message: str, thread_id: str | None = None, config: dict | None = None
    ) -> AsyncIterator[Any]:
        """Async generator to stream events from the agent."""
        ...


