from typing import List, Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from deepeye.graph.state import AgentState
from langchain_core.messages import ToolMessage

@tool
def create_plan(steps: List[str], tool_call_id: Annotated[str, InjectedToolCallId]) -> Annotated[Command, "The result of creating the plan"]:
    """
    Create a new execution plan with a list of steps.
    Example: ["Query database for sales", "Plot sales trend"]
    """
    return Command(
        update={
            "plan": steps,
            "completed_steps": [],
            "messages": [ToolMessage(content="Plan Created.", tool_call_id=tool_call_id)]
        }
    )

@tool
def update_plan(steps: List[str], tool_call_id: Annotated[str, InjectedToolCallId]) -> Annotated[Command, "The result of updating the plan"]:
    """
    Update the current plan with new steps. Use this if the original plan is invalid.
    """
    return Command(
        update={
            "plan": steps,
            "messages": [ToolMessage(content="Plan Updated.", tool_call_id=tool_call_id)]
        }
    )

@tool
def mark_step_done(
    step_index: int, 
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Annotated[Command, "The result of marking a step as done"]:
    """
    Mark a step as completed.
    Args:
        step_index: The 1-based index of the step to mark as done.
    """
    current_completed = set(state.get("completed_steps", []) or [])
    current_completed.add(step_index)
    
    return Command(
        update={
            "completed_steps": list(current_completed),
            "messages": [ToolMessage(content=f"Step {step_index} marked as done.", tool_call_id=tool_call_id)]
        }
    )

