"""Chat workflow helpers."""

from app.schemas import AgentInput
from app.tasks.agent_tasks import run_agent_workflow


def start_agent_workflow(
    session_id: str,
    message: str,
    datasource_ids: list[str] | None = None,
) -> str:
    """Start agent workflow and return task ID."""
    task = run_agent_workflow.delay(
        AgentInput(
            session_id=session_id,
            user_input=message,
            datasource_ids=datasource_ids,
        ).model_dump()
    )
    return task.id
