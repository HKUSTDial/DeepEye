from __future__ import annotations

from typing import Callable

_progress_publishers: dict[str, Callable[[str], None]] = {}
_workflow_to_session: dict[str, str] = {}


def get_progress_publisher(session_id: str) -> Callable[[str], None] | None:
    return _progress_publishers.get(session_id)


def get_progress_publisher_by_workflow_id(workflow_id: str) -> Callable[[str], None] | None:
    session_id = _workflow_to_session.get(workflow_id)
    if session_id:
        return _progress_publishers.get(session_id)
    return None


def get_session_id_by_workflow_id(workflow_id: str) -> str | None:
    return _workflow_to_session.get(workflow_id)


def register_workflow_progress(
    session_id: str,
    workflow_id: str,
    publisher: Callable[[str], None],
) -> None:
    _progress_publishers[session_id] = publisher
    _workflow_to_session[workflow_id] = session_id


def clear_workflow_runtime_state(session_id: str) -> None:
    _progress_publishers.pop(session_id, None)
    workflows_to_remove = [
        workflow_id
        for workflow_id, mapped_session in _workflow_to_session.items()
        if mapped_session == session_id
    ]
    for workflow_id in workflows_to_remove:
        _workflow_to_session.pop(workflow_id, None)
