from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent

DEFAULT_KNOWLEDGE_BASE_AGENT_SYSTEM_PROMPT = """You are a knowledge-base reasoning agent.
Follow the backend-provided system prompt and tool contracts exactly.
"""


class KnowledgeBaseAgent(ReActAgent):
    """Agent that queries knowledge bases and answers."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: list | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        system_prompt: str = DEFAULT_KNOWLEDGE_BASE_AGENT_SYSTEM_PROMPT,
        max_steps: int = 30,
    ):
        super().__init__(
            model=model,
            tools=tools or [],
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )
