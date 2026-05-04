"""Tests for workflow agent run service helpers."""

import os
import uuid

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, User, WorkflowDraft
from app.workflow.services import agent_runs as workflow_agent_runs
from app.workflow.services.targets import save_workflow_draft


def _build_test_session_local():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _create_user(db, email: str = "alice@example.com") -> User:
    user = User(
        email=email,
        username=email.split("@", maxsplit=1)[0],
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_session(db, user: User) -> ChatSession:
    session = ChatSession(user_id=user.id, title="Thread A")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.mark.asyncio
async def test_run_agent_workflow_draft_returns_raw_result_and_definition(monkeypatch) -> None:
    session_local = _build_test_session_local()
    db = session_local()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        definition = {"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}}
        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            definition=definition,
            name="analysis",
            source="workflow_agent",
        )
        session_id = str(session.id)
        draft_id = str(draft.id)
        user_id = str(user.id)
    finally:
        db.close()

    calls = []

    async def fake_service_run_workflow_draft(db, user_id, session_id_arg, draft_id_arg, *, turn_id=None, run_id=None):
        calls.append((str(user_id), session_id_arg, draft_id_arg, turn_id, run_id))
        return {"status": "success", "outputs": {"answer": "done"}}

    monkeypatch.setattr(workflow_agent_runs, "SessionLocal", session_local)
    monkeypatch.setattr(workflow_agent_runs, "service_run_workflow_draft", fake_service_run_workflow_draft)

    outcome = await workflow_agent_runs.run_agent_workflow_draft(
        session_id=session_id,
        draft_id=draft_id,
        turn_id="turn-1",
    )

    assert not outcome.is_failure
    assert outcome.draft_id == draft_id
    assert outcome.workflow_definition == definition
    assert outcome.raw_result == {"status": "success", "outputs": {"answer": "done"}}
    assert calls == [(user_id, session_id, draft_id, "turn-1", None)]


@pytest.mark.asyncio
async def test_create_and_run_agent_workflow_draft_persists_before_running(monkeypatch) -> None:
    session_local = _build_test_session_local()
    db = session_local()
    try:
        user = _create_user(db, email="bob@example.com")
        session = _create_session(db, user)
        session_id = str(session.id)
    finally:
        db.close()

    definition = {"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}}

    async def fake_service_run_workflow_draft(db, user_id, session_id_arg, draft_id_arg, *, turn_id=None, run_id=None):
        draft = db.get(WorkflowDraft, uuid.UUID(draft_id_arg))
        assert draft is not None
        assert draft.definition == definition
        assert draft.file_path == "/workspace/workflow/FreshRun.json"
        return {"status": "success", "outputs": {}}

    monkeypatch.setattr(workflow_agent_runs, "SessionLocal", session_local)
    monkeypatch.setattr(workflow_agent_runs, "service_run_workflow_draft", fake_service_run_workflow_draft)

    outcome = await workflow_agent_runs.create_and_run_agent_workflow_draft(
        session_id=session_id,
        definition=definition,
        name="Fresh Run",
    )

    assert not outcome.is_failure
    assert outcome.workflow_definition == definition
    assert outcome.raw_result == {"status": "success", "outputs": {}}


@pytest.mark.asyncio
async def test_run_agent_workflow_draft_reports_missing_session(monkeypatch) -> None:
    session_local = _build_test_session_local()
    monkeypatch.setattr(workflow_agent_runs, "SessionLocal", session_local)

    outcome = await workflow_agent_runs.run_agent_workflow_draft(
        session_id=str(uuid.uuid4()),
        draft_id=str(uuid.uuid4()),
    )

    assert outcome.is_failure
    assert outcome.error_type == "session_not_found"
    assert outcome.error == "Session not found."
