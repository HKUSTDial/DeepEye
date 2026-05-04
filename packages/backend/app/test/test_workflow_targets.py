"""Tests for workflow draft target resolution helpers."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, User
from app.workflow.services.targets import resolve_workflow_target, save_workflow_draft


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


def test_save_workflow_draft_uses_name_as_stable_target():
    db = _build_test_db()
    try:
        user = _create_user(db)
        session = _create_session(db, user)

        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            definition={"root": {"nodes": {}, "edges": {}}},
            name="Revenue Analysis",
            source="workflow_agent",
        )

        assert draft.file_path == "/workspace/workflow/RevenueAnalysis.json"
        assert draft.version == 1
    finally:
        db.close()


def test_save_workflow_draft_updates_existing_draft_by_id():
    db = _build_test_db()
    try:
        user = _create_user(db, email="bob@example.com")
        session = _create_session(db, user)

        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            definition={"root": {"nodes": {}, "edges": {}}},
            name="video",
            source="workflow_agent",
        )
        updated = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            draft_id=str(draft.id),
            definition={"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}},
            source="workflow_agent",
        )

        assert updated.id == draft.id
        assert updated.file_path == draft.file_path
        assert updated.version == 2
        assert "n1" in updated.definition["root"]["nodes"]
    finally:
        db.close()


def test_save_workflow_draft_is_idempotent_for_duplicate_payload():
    db = _build_test_db()
    try:
        user = _create_user(db, email="dave@example.com")
        session = _create_session(db, user)
        definition = {"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}}

        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            definition=definition,
            name="dup-check",
            source="workflow_agent",
        )
        duplicate = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            draft_id=str(draft.id),
            definition=definition,
            source="workflow_agent",
        )

        assert duplicate.id == draft.id
        assert duplicate.version == 1
        assert duplicate.file_path == draft.file_path
    finally:
        db.close()


def test_resolve_workflow_target_rejects_cross_session_draft_access():
    db = _build_test_db()
    try:
        user = _create_user(db, email="carol@example.com")
        session_a = _create_session(db, user)
        session_b = _create_session(db, user)

        draft = save_workflow_draft(
            db,
            session_id=session_a.id,
            user_id=user.id,
            definition={"root": {"nodes": {}, "edges": {}}},
            name="shared",
            source="workflow_agent",
        )

        try:
            resolve_workflow_target(
                db,
                session_b.id,
                draft_id=str(draft.id),
            )
            assert False, "expected resolve_workflow_target to reject cross-session access"
        except ValueError as exc:
            assert "does not belong" in str(exc)
    finally:
        db.close()
