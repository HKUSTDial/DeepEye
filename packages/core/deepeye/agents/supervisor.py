from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent
from deepeye.graph.state import AgentState
from deepeye.tools.planning_tools import create_plan, mark_step_done, update_plan

SUPERVISOR_SYSTEM_PROMPT = """You are a Workflow Orchestrator.
Tools: workflow agent (design + run), run_workflow_from_file, plan/update/mark steps, query_knowledge_base for knowledge base.

Current Session Context:
{datasources_context}

Decision policy:
- If the user wants to analyze data but {datasources_context} indicates no data sources are selected, proactively ASK the user to upload files or connect a database. Otherwise, if {datasources_context} shows "Available Data Sources", the data is ready and you should proceed with workflow design/execution.
- For ANY request that needs pipeline execution (including data video, report generation, dashboard generation, SQL/data processing, or file generation), call the workflow agent with a clear goal and known literals (tables/columns/filters/paths). Do NOT invent values; pass user-provided text verbatim.
- Architecture rule: video/report/dashboard must be executed as workflow nodes (e.g., `video.generator`, `report.generate`, `data.generate_dashboard`) rather than direct one-shot tools.
- If the user references a knowledge base (e.g., "@我的日记") or asks about information likely stored there, call query_knowledge_base instead of the workflow agent.
- If the request is simple and doesn’t need a workflow, answer directly (no tool).
- Plan only when multiple steps are required; otherwise skip planning and call the appropriate tool directly.

Execution rules:
- Keep responses concise. After the workflow agent finishes, summarize in 1–2 sentences; do NOT paste workflow JSON.
- Preserve user language and literal values end-to-end (class names, exam types, file paths, etc.).

Current Plan:
{plan}
"""


class SupervisorAgent(ReActAgent):
    """The main orchestrator agent that uses a Tool-Based Planning architecture."""

    def __init__(
        self, 
        model: BaseChatModel, 
        tools: list[Any], 
        checkpointer: BaseCheckpointSaver | None = None,
        max_steps: int = 50,
    ):
        planning_tools = [create_plan, update_plan, mark_step_done]
        super().__init__(model, tools + planning_tools, system_prompt="", checkpointer=checkpointer, max_steps=max_steps)

    async def _call_model(self, state: AgentState, config: RunnableConfig) -> dict:
        """Override to inject dynamic plan into system prompt. Callbacks propagate via config."""
        messages = state["messages"]
        plan = state.get("plan") or []
        completed = set(state.get("completed_steps") or [])

        # Get dynamic context from config
        datasources_context = config.get("configurable", {}).get("datasources_context", "No data sources selected.")

        plan_str = "\n".join(f"{i + 1}. {'[x]' if i + 1 in completed else '[ ]'} {s}" for i, s in enumerate(plan)) if plan else "No plan yet."
        system_msg = SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(plan=plan_str, datasources_context=datasources_context))

        response = await self._bound_model.ainvoke([system_msg] + list(messages), config=config)
        return {"messages": [response]}
