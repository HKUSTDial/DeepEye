from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from deepeye.agents.base import ReActAgent
from deepeye.graph.state import AgentState
from deepeye.tools.planning_tools import create_plan, update_plan, mark_step_done

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
    """
    The main orchestrator agent that uses a Tool-Based Planning architecture.
    """
    def __init__(
        self, 
        model: BaseChatModel, 
        tools: List[any], 
        system_prompt: str = None,
        checkpointer: Optional[any] = None
    ):
        # Auto-inject planning tools
        planning_tools = [create_plan, update_plan, mark_step_done]
        all_tools = tools + planning_tools
        
        # We don't pass system_prompt to super init because we manage it dynamically
        super().__init__(model, all_tools, system_prompt="", checkpointer=checkpointer)

    async def _call_model(self, state: AgentState):
        """Override _call_model to inject Plan into System Prompt."""
        messages = state["messages"]
        plan = state.get("plan", [])
        completed = set(state.get("completed_steps", []) or [])
        
        if plan:
            plan_lines = []
            for i, step in enumerate(plan):
                idx = i + 1
                status = "[x]" if idx in completed else "[ ]"
                plan_lines.append(f"{idx}. {status} {step}")
            plan_str = "\n".join(plan_lines)
        else:
            plan_str = "No plan yet."
        
        system_msg = SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(plan=plan_str))
        
        # Prepend system message
        messages_with_system = [system_msg] + list(messages)
        
        response = await self.model.ainvoke(messages_with_system)
        return {"messages": [response]}
