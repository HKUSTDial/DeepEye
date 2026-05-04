"""Tests for workflow agent draft persistence helpers."""

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
from app.workflow.services import agent_drafts as workflow_agent_drafts
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
async def test_save_agent_workflow_draft_persists_and_syncs_file(monkeypatch) -> None:
    session_local = _build_test_session_local()
    db = session_local()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        definition = {"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}}
        user_id = str(user.id)
        session_id = str(session.id)
    finally:
        db.close()

    writes = []

    async def fake_write_workflow_definition_to_file(session_id: str, path: str, workflow: dict) -> None:
        writes.append((session_id, path, workflow))

    monkeypatch.setattr(workflow_agent_drafts, "SessionLocal", session_local)
    monkeypatch.setattr(
        workflow_agent_drafts,
        "write_workflow_definition_to_file",
        fake_write_workflow_definition_to_file,
    )

    saved = await workflow_agent_drafts.save_agent_workflow_draft(
        session_id=session_id,
        user_id=user_id,
        definition=definition,
        name="Revenue Analysis",
    )

    assert saved.file_path == "/workspace/workflow/RevenueAnalysis.json"
    assert writes == [(session_id, saved.file_path, definition)]

    verify_db = session_local()
    try:
        draft = verify_db.get(WorkflowDraft, uuid.UUID(saved.draft_id))
        assert draft is not None
        assert draft.definition == definition
        assert draft.file_path == saved.file_path
    finally:
        verify_db.close()


@pytest.mark.asyncio
async def test_read_workflow_definition_prefers_persisted_draft(monkeypatch) -> None:
    session_local = _build_test_session_local()
    db = session_local()
    try:
        user = _create_user(db, email="bob@example.com")
        session = _create_session(db, user)
        definition = {"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}}
        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            definition=definition,
            name="drafted",
            source="workflow_agent",
        )
        draft_id = str(draft.id)
        session_id = str(session.id)
    finally:
        db.close()

    async def fail_read_workflow_file(session_id: str, path: str) -> dict:
        raise AssertionError("draft-backed reads should not hit the sandbox file")

    monkeypatch.setattr(workflow_agent_drafts, "SessionLocal", session_local)
    monkeypatch.setattr(workflow_agent_drafts, "read_workflow_file", fail_read_workflow_file)

    result = await workflow_agent_drafts.read_workflow_definition(session_id=session_id, draft_id=draft_id)

    assert result.status == "success"
    assert result.workflow == definition
    assert result.draft_id == draft_id
    assert result.to_tool_response() == {
        "status": "success",
        "draft_id": draft_id,
        "workflow": definition,
    }


@pytest.mark.asyncio
async def test_read_workflow_definition_falls_back_to_normalized_file_path(monkeypatch) -> None:
    session_local = _build_test_session_local()
    db = session_local()
    try:
        user = _create_user(db, email="carol@example.com")
        session = _create_session(db, user)
        session_id = str(session.id)
    finally:
        db.close()

    reads = []
    definition = {"root": {"nodes": {"legacy": {"id": "legacy"}}, "edges": {}}}

    async def fake_read_workflow_file(session_id: str, path: str) -> dict:
        reads.append((session_id, path))
        return definition

    monkeypatch.setattr(workflow_agent_drafts, "SessionLocal", session_local)
    monkeypatch.setattr(workflow_agent_drafts, "read_workflow_file", fake_read_workflow_file)

    result = await workflow_agent_drafts.read_workflow_definition(
        session_id=session_id,
        file_path="/tmp/Legacy Flow.json",
    )

    assert result.status == "success"
    assert result.workflow == definition
    assert reads == [(session_id, "/workspace/workflow/LegacyFlow.json")]
