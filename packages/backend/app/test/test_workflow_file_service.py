"""Tests for tracked workflow file run preparation."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, User
from app.workflow.services.file_service import (
    _summarize_failed_context,
    prepare_tracked_workflow_draft_run,
    prepare_tracked_workflow_file_run,
)
from app.workflow.services.tracking import create_chat_turn
from deepeye.workflows.models import Graph, Node
from deepeye.workflows.runtime import ExecutionContext, NodeRun


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


def test_prepare_tracked_workflow_file_run_reuses_existing_ids():
    db = _build_test_db()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Run saved workflow")

        first_definition = {"root": {"nodes": {}, "edges": {}}}
        tracked_turn, tracked_draft, tracked_run = prepare_tracked_workflow_file_run(
            db,
            user_id=user.id,
            session_id=str(session.id),
            path="/workspace/workflow/demo.json",
            definition=first_definition,
            turn_id=str(turn.id),
        )

        assert tracked_turn is not None
        assert tracked_draft is not None
        assert tracked_run is not None
        assert tracked_draft.file_path == "/workspace/workflow/demo.json"
        assert tracked_draft.source == "workflow_file"
        assert tracked_run.draft_id == tracked_draft.id
        assert tracked_run.status == "running"

        next_definition = {"root": {"nodes": {"report": {"id": "report"}}, "edges": {}}}
        tracked_turn_2, tracked_draft_2, tracked_run_2 = prepare_tracked_workflow_file_run(
            db,
            user_id=user.id,
            session_id=str(session.id),
            path="/workspace/workflow/demo.json",
            definition=next_definition,
            turn_id=str(turn.id),
            draft_id=str(tracked_draft.id),
            run_id=str(tracked_run.id),
        )

        assert tracked_turn_2.id == tracked_turn.id
        assert tracked_draft_2.id == tracked_draft.id
        assert tracked_run_2.id == tracked_run.id
        assert tracked_draft_2.definition == next_definition
        assert tracked_run_2.draft_id == tracked_draft.id
        assert tracked_run_2.turn_id == turn.id
    finally:
        db.close()


def test_prepare_tracked_workflow_draft_run_reuses_existing_draft():
    db = _build_test_db()
    try:
        user = _create_user(db, email="draft@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Run tracked draft")

        _, tracked_draft, tracked_run = prepare_tracked_workflow_file_run(
            db,
            user_id=user.id,
            session_id=str(session.id),
            path="/workspace/workflow/draft-demo.json",
            definition={"root": {"nodes": {"n1": {"id": "n1"}}, "edges": {}}},
            turn_id=str(turn.id),
        )

        next_turn = create_chat_turn(db, session.id, user.id, "Run draft again")
        tracked_turn_2, tracked_draft_2, tracked_run_2, path = prepare_tracked_workflow_draft_run(
            db,
            user_id=user.id,
            session_id=str(session.id),
            draft_id=str(tracked_draft.id),
            turn_id=str(next_turn.id),
        )

        assert tracked_turn_2.id == next_turn.id
        assert tracked_draft_2.id == tracked_draft.id
        assert tracked_draft_2.source == "workflow_file"
        assert tracked_run_2.id != tracked_run.id
        assert tracked_run_2.draft_id == tracked_draft.id
        assert tracked_run_2.turn_id == next_turn.id
        assert tracked_run_2.source == "workflow_draft"
        assert path == tracked_draft.file_path
    finally:
        db.close()


def test_summarize_failed_context_reports_failed_node_details():
    graph = Graph(
        nodes={
            "read_file": Node(id="read_file", type="datasource.read"),
            "join_data": Node(id="join_data", type="python.code"),
        },
        edges={},
    )
    context = ExecutionContext(
        workflow_id="wf-1",
        status="failed",
        runs={
            "read_file": NodeRun(node_id="read_file", status="success"),
            "join_data": NodeRun(node_id="join_data", status="failed", error="KeyError: city"),
        },
    )

    error, details = _summarize_failed_context(graph, context)

    assert error == "Workflow execution failed at node join_data (python.code): KeyError: city"
    assert details == [
        {
            "node_id": "join_data",
            "node_type": "python.code",
            "message": "KeyError: city",
        }
    ]
