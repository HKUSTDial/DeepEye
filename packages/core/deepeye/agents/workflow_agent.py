from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.graph.state import AgentState

DEFAULT_WORKFLOW_AGENT_SYSTEM_PROMPT = """You are a workflow planning agent.
Follow the backend-provided system prompt and tool contracts exactly.
"""


class WorkflowAgent(ReActAgent):
    """Agent that outputs workflow JSON definitions."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: list | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        system_prompt: str = DEFAULT_WORKFLOW_AGENT_SYSTEM_PROMPT,
        max_steps: int = 50,
        stop_condition: Callable[[], dict[str, Any] | None] | None = None,
    ):
        self.stop_condition = stop_condition
        super().__init__(
            model=model,
            tools=tools or [],
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        terminal_failure = self.stop_condition() if self.stop_condition else None
        if terminal_failure:
            content = terminal_failure.get("error_summary") or terminal_failure.get("error") or "Workflow planning stopped."
            return {"messages": [AIMessage(content=content)]}
        return await super()._call_model(state, config)
