"""Agent Factory - unified agent creation."""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.supervisor import DEFAULT_SUPERVISOR_SYSTEM_PROMPT, SupervisorAgent


class AgentFactory:
    """Creates configured agent instances."""

    def __init__(
        self,
        model: BaseChatModel,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.model = model
        self.checkpointer = checkpointer

    def create_supervisor(self, tools: list[Any], system_prompt_template: str | None = None) -> SupervisorAgent:
        """Create supervisor agent with given tools."""
        return SupervisorAgent(
            model=self.model,
            tools=tools,
            system_prompt_template=system_prompt_template or DEFAULT_SUPERVISOR_SYSTEM_PROMPT,
            checkpointer=self.checkpointer,
        )
