"""Agent state definitions for LangGraph"""

from typing import Annotated, Sequence, TypeVar

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

T = TypeVar("T")


def replace_if_set(old: T, new: T) -> T:
    """Generic reducer: replace old value if new is provided."""
    return old if new is None else new


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    plan: Annotated[list[str], replace_if_set]
    completed_steps: Annotated[list[int], replace_if_set]
