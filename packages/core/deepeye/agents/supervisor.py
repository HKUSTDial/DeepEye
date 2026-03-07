import ast
import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.graph.state import AgentState

DEFAULT_SUPERVISOR_SYSTEM_PROMPT = """You are an orchestration agent.

Current Session Context:
{datasources_context}
"""


class SupervisorAgent(ReActAgent):
    """The main orchestrator agent."""

    def __init__(
        self, 
        model: BaseChatModel, 
        tools: list[Any], 
        system_prompt_template: str = DEFAULT_SUPERVISOR_SYSTEM_PROMPT,
        checkpointer: BaseCheckpointSaver | None = None,
        max_steps: int = 50,
    ):
        self.system_prompt_template = system_prompt_template
        super().__init__(model, tools, system_prompt="", checkpointer=checkpointer, max_steps=max_steps)

    @staticmethod
    def _parse_tool_payload(content: Any) -> dict[str, Any] | None:
        if isinstance(content, dict):
            return content
        if isinstance(content, list):
            joined = "".join(part for part in content if isinstance(part, str))
            content = joined
        if not isinstance(content, str) or not content.strip():
            return None
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            try:
                parsed = ast.literal_eval(content)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None

    @classmethod
    def _extract_workflow_final_answer(cls, messages: list[Any]) -> str | None:
        if not messages:
            return None
        last_message = messages[-1]
        if not isinstance(last_message, ToolMessage):
            return None
        if getattr(last_message, "name", None) != "workflow_agent":
            return None
        payload = cls._parse_tool_payload(last_message.content)
        if not isinstance(payload, dict):
            return None
        final_answer = payload.get("final_answer")
        if isinstance(final_answer, str) and final_answer.strip():
            return final_answer.strip()
        return None

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        """Override to inject dynamic plan into system prompt. Callbacks propagate via config."""
        messages = state["messages"]
        final_answer = self._extract_workflow_final_answer(list(messages))
        if final_answer:
            return {"messages": [AIMessage(content=final_answer)]}

        # Get dynamic context from config
        datasources_context = config.get("configurable", {}).get("datasources_context", "No data sources selected.")
        prompt_template = config.get("configurable", {}).get("supervisor_prompt_template", self.system_prompt_template)

        system_msg = SystemMessage(content=prompt_template.format(datasources_context=datasources_context))

        response = await self._bound_model.ainvoke([system_msg] + list(messages), config=config)
        return {"messages": [response]}
