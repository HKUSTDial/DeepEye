"""Internal data transfer schemas"""

from pydantic import BaseModel


class AgentInput(BaseModel):
    """Input schema for Agent Workflow Task"""

    session_id: str
    user_input: str
    datasource_ids: list[str] | None = None
