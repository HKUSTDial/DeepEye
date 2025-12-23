from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.graph.state import AgentState
from deepeye.tools.planning_tools import create_plan, mark_step_done, update_plan

SUPERVISOR_SYSTEM_PROMPT = """You are a helpful and intelligent Data Analysis Assistant.
Your goal is to help the user with their data analysis tasks by coordinating with specialized sub-agents.

Current Plan:
{plan}

Guidelines:
1. **CREATE PLAN**: If you don't have a plan yet (or "No plan yet"), analyze the user request and call `create_plan` with a list of steps.
2. **EXECUTE**: Follow the plan step-by-step. Call the appropriate sub-agent tools.
3. **MARK DONE**: After successfully finishing a step (and getting the result), you MUST call `mark_step_done(index)`.
4. **THINK FIRST**: Before calling any tool, you MUST output a brief thought explaining your reasoning.
5. If the plan is invalid, call `update_plan`.
"""


class SupervisorAgent(ReActAgent):
    """The main orchestrator agent that uses a Tool-Based Planning architecture."""

    def __init__(self, model: BaseChatModel, tools: list[Any], checkpointer: BaseCheckpointSaver | None = None):
        planning_tools = [create_plan, update_plan, mark_step_done]
        super().__init__(model, tools + planning_tools, system_prompt="", checkpointer=checkpointer)

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        """Override to inject dynamic plan into system prompt. Callbacks propagate via config."""
        messages = state["messages"]
        plan = state.get("plan") or []
        completed = set(state.get("completed_steps") or [])

        plan_str = "\n".join(f"{i + 1}. {'[x]' if i + 1 in completed else '[ ]'} {s}" for i, s in enumerate(plan)) if plan else "No plan yet."
        system_msg = SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(plan=plan_str))

        response = await self._bound_model.ainvoke([system_msg] + list(messages), config=config)
        return {"messages": [response]}
