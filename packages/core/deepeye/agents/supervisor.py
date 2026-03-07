from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.graph.state import AgentState
from deepeye.tools.planning_tools import create_plan, mark_step_done, update_plan

DEFAULT_SUPERVISOR_SYSTEM_PROMPT = """You are an orchestration agent.

Current Session Context:
{datasources_context}

Current Plan:
{plan}
"""


class SupervisorAgent(ReActAgent):
    """The main orchestrator agent that uses a Tool-Based Planning architecture."""

    def __init__(
        self, 
        model: BaseChatModel, 
        tools: list[Any], 
        system_prompt_template: str = DEFAULT_SUPERVISOR_SYSTEM_PROMPT,
        checkpointer: BaseCheckpointSaver | None = None,
        max_steps: int = 50,
    ):
        planning_tools = [create_plan, update_plan, mark_step_done]
        self.system_prompt_template = system_prompt_template
        super().__init__(model, tools + planning_tools, system_prompt="", checkpointer=checkpointer, max_steps=max_steps)

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        """Override to inject dynamic plan into system prompt. Callbacks propagate via config."""
        messages = state["messages"]
        plan = state.get("plan") or []
        completed = set(state.get("completed_steps") or [])

        # Get dynamic context from config
        datasources_context = config.get("configurable", {}).get("datasources_context", "No data sources selected.")
        prompt_template = config.get("configurable", {}).get("supervisor_prompt_template", self.system_prompt_template)

        plan_str = "\n".join(f"{i + 1}. {'[x]' if i + 1 in completed else '[ ]'} {s}" for i, s in enumerate(plan)) if plan else "No plan yet."
        system_msg = SystemMessage(content=prompt_template.format(plan=plan_str, datasources_context=datasources_context))

        response = await self._bound_model.ainvoke([system_msg] + list(messages), config=config)
        return {"messages": [response]}
