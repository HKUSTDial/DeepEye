"""Service helpers."""

from typing import Any

__all__ = ["start_agent_workflow", "get_or_create_session"]


def start_agent_workflow(*args: Any, **kwargs: Any):
    from app.services.chat_service import start_agent_workflow as _start

    return _start(*args, **kwargs)


def get_or_create_session(*args: Any, **kwargs: Any):
    from app.services.session_service import get_or_create_session as _get

    return _get(*args, **kwargs)
