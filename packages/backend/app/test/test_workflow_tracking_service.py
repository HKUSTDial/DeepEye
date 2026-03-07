"""Tests for workflow tracking persistence helpers."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, User
from app.repositories import MessageRepository
from app.schemas import UserMessage
from app.services.workflow_tracking_service import (
    build_workspace_state,
    create_chat_turn,
    create_tracked_workflow_run,
    finalize_tracked_workflow_run,
    replace_workflow_artifacts,
    upsert_workflow_draft,
)


def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_local()


def _create_user(db, email: str = "alice@example.com") -> User:
    user = User(
        email=email,
        username="alice",
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


def test_workflow_tracking_persists_turn_draft_run_artifacts_and_workspace_state():
    db = _build_test_db()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        user_message = MessageRepository(db).append(str(session.id), UserMessage(content="Analyze revenue"))

        turn = create_chat_turn(
            db,
            session.id,
            user.id,
            "Analyze revenue",
            user_message_id=user_message.id,
        )

        first_draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            turn_id=turn.id,
            file_path="/workspace/workflow/revenue.json",
            definition={"root": {"nodes": {}, "edges": {}}},
        )
        second_draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            turn_id=turn.id,
            file_path="/workspace/workflow/revenue.json",
            definition={"root": {"nodes": {"report": {"id": "report"}}, "edges": {}}},
        )

        assert first_draft.id == second_draft.id
        assert second_draft.version == 2

        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            turn_id=turn.id,
            draft_id=second_draft.id,
            file_path=second_draft.file_path,
        )

        artifacts = replace_workflow_artifacts(
            db,
            run,
            [{"kind": "report", "report_path": "/workspace/analysis_report.html"}],
        )
        finalized_run = finalize_tracked_workflow_run(
            db,
            run,
            status="success",
            result={"status": "success"},
            artifacts=[artifact.payload for artifact in artifacts],
        )

        state = build_workspace_state(db, session.id)

        assert state["turn"].id == turn.id
        assert state["turn"].status == "summarizing"
        assert state["draft"].id == second_draft.id
        assert state["run"].id == finalized_run.id
        assert state["run"].draft_id == second_draft.id
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0].payload["kind"] == "report"
    finally:
        db.close()


def test_message_append_keeps_primary_key_accessible_after_session_close():
    db = _build_test_db()
    try:
        user = _create_user(db, email="bob@example.com")
        session = _create_session(db, user)
        message = MessageRepository(db).append(str(session.id), UserMessage(content="Hello"))
        message_id = message.id
    finally:
        db.close()

    assert message_id is not None


def test_workspace_state_falls_back_to_latest_session_run_without_turn():
    db = _build_test_db()
    try:
        user = _create_user(db, email="carol@example.com")
        session = _create_session(db, user)
        create_chat_turn(db, session.id, user.id, "Previous chat-only request")

        draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            file_path="/workspace/workflow/manual.json",
            definition={"root": {"nodes": {"manual": {"id": "manual"}}, "edges": {}}},
            source="workflow_file",
        )
        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            draft_id=draft.id,
            file_path=draft.file_path,
            source="workflow_file",
        )
        artifacts = replace_workflow_artifacts(
            db,
            run,
            [{"kind": "dashboard", "dashboard_url": "http://localhost:3000/dashboard/manual"}],
        )
        finalize_tracked_workflow_run(
            db,
            run,
            status="success",
            result={"status": "success"},
            artifacts=[artifact.payload for artifact in artifacts],
        )

        state = build_workspace_state(db, session.id)

        assert state["turn"] is None
        assert state["draft"].id == draft.id
        assert state["run"].id == run.id
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0].payload["kind"] == "dashboard"
    finally:
        db.close()
