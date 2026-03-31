"""Process-local DB session helpers for Celery tasks."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_ENGINE_PID: int | None = None
_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _ENGINE_PID, _ENGINE, _SESSION_FACTORY

    current_pid = os.getpid()
    if _SESSION_FACTORY is None or _ENGINE is None or _ENGINE_PID != current_pid:
        _ENGINE = create_engine(settings.SQLALCHEMY_DATABASE_URL)
        _SESSION_FACTORY = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)
        _ENGINE_PID = current_pid
    return _SESSION_FACTORY


def open_task_session() -> Session:
    return _get_session_factory()()


@contextmanager
def task_session_scope() -> Iterator[Session]:
    db = open_task_session()
    try:
        yield db
    finally:
        db.close()
