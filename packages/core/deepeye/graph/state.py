from typing import Annotated, Sequence, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def update_plan(old_plan: List[str], new_plan: List[str]) -> List[str]:
    """Reducer to update the plan. If new_plan is provided, it replaces the old one."""
    if new_plan is None:
        return old_plan
    return new_plan

def update_completed_steps(old_steps: List[int], new_steps: List[int]) -> List[int]:
    """Reducer to update completed steps."""
    if new_steps is None:
        return old_steps
    return new_steps

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    plan: Annotated[List[str], update_plan]
    completed_steps: Annotated[List[int], update_completed_steps]
