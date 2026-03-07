"""Service helpers."""

from typing import Any

__all__ = [
    "start_agent_workflow",
    "get_or_create_session",
    "attach_datasource_to_session",
    "detach_datasource_from_session",
    "get_session_attachment_ids",
    "list_session_attachments",
]


def start_agent_workflow(*args: Any, **kwargs: Any):
    from app.services.chat_service import start_agent_workflow as _start

    return _start(*args, **kwargs)


def get_or_create_session(*args: Any, **kwargs: Any):
    from app.services.session_service import get_or_create_session as _get

    return _get(*args, **kwargs)


def attach_datasource_to_session(*args: Any, **kwargs: Any):
    from app.services.session_attachment_service import attach_datasource_to_session as _attach

    return _attach(*args, **kwargs)


def detach_datasource_from_session(*args: Any, **kwargs: Any):
    from app.services.session_attachment_service import detach_datasource_from_session as _detach

    return _detach(*args, **kwargs)


def get_session_attachment_ids(*args: Any, **kwargs: Any):
    from app.services.session_attachment_service import get_session_attachment_ids as _get_ids

    return _get_ids(*args, **kwargs)


def list_session_attachments(*args: Any, **kwargs: Any):
    from app.services.session_attachment_service import list_session_attachments as _list

    return _list(*args, **kwargs)
