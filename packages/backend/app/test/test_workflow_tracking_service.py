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
from app.schemas import AssistantMessage, UserMessage
from app.workflow.services.tracking import (
    build_workspace_state,
    build_workspace_state_for_turn,
    create_chat_turn,
    create_tracked_workflow_run,
    fail_chat_turn_record,
    finalize_tracked_workflow_run,
    replace_workflow_artifacts,
    upsert_workflow_draft,
)
from app.workflow.services.workspace_state import dedupe_summary_artifact_references


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
            file_path="/workspace/workflow/revenue_v2.json",
            definition={"root": {"nodes": {"report": {"id": "report"}}, "edges": {}}},
        )

        assert first_draft.id == second_draft.id
        assert second_draft.version == 2
        assert second_draft.file_path == "/workspace/workflow/revenue_v2.json"
        assert second_draft.display_name == "revenue_v2"

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
        assert state["artifacts"][0].payload["status"] == "ready"
        assert state["artifacts"][0].payload["preview"] == {
            "mime_type": "text/html",
            "path": "/workspace/analysis_report.html",
            "type": "file",
        }
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


def test_failed_workflow_run_does_not_move_turn_to_summarizing() -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="failed-run@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Run a fragile workflow")
        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            turn_id=turn.id,
        )

        finalized = finalize_tracked_workflow_run(
            db,
            run,
            status="failed",
            result={"status": "failed"},
            error="workflow failed",
            artifacts=[],
        )
        state = build_workspace_state_for_turn(db, turn.id)

        assert finalized.status == "failed"
        assert state["turn"].status == "running"
    finally:
        db.close()


def test_fail_chat_turn_record_persists_assistant_message_id(monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="trace@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Analyze revenue")
        assistant_message = MessageRepository(db).append(
            str(session.id),
            AssistantMessage(content="Workflow planning failed."),
        )
        assistant_message_id = assistant_message.id
        monkeypatch.setattr("app.workflow.services.tracking.SessionLocal", lambda: db)
        failed = fail_chat_turn_record(turn.id, "workflow failed", assistant_message_id=assistant_message_id)

        assert failed is not None
        assert failed.status == "failed"
        assert failed.assistant_message_id == assistant_message_id
    finally:
        db.close()


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
        assert draft.display_name == "manual"
        assert state["run"].id == run.id
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0].payload["kind"] == "dashboard"
        assert state["artifacts"][0].payload["preview"] == {
            "type": "url",
            "url": "http://localhost:3000/dashboard/manual",
        }
    finally:
        db.close()


def test_workspace_state_for_turn_uses_turn_scoped_run_and_artifacts():
    db = _build_test_db()
    try:
        user = _create_user(db, email="dave@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Build a dashboard")

        draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            turn_id=turn.id,
            file_path="/workspace/workflow/dashboard.json",
            definition={"root": {"nodes": {"dash": {"id": "dash"}}, "edges": {}}},
        )
        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            turn_id=turn.id,
            draft_id=draft.id,
            file_path=draft.file_path,
        )
        artifacts = replace_workflow_artifacts(
            db,
            run,
            [{"kind": "dashboard", "dashboard_url": "http://localhost:3000/dashboard/demo"}],
        )
        finalize_tracked_workflow_run(
            db,
            run,
            status="success",
            result={"status": "success", "outputs": {"dash": {"dashboard_url": "http://localhost:3000/dashboard/demo"}}},
            artifacts=[artifact.payload for artifact in artifacts],
        )

        state = build_workspace_state_for_turn(db, turn.id)

        assert state["turn"].id == turn.id
        assert state["draft"].id == draft.id
        assert state["run"].id == run.id
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0].payload["kind"] == "dashboard"
        assert state["artifacts"][0].payload["payload"]["dashboard_url"] == "http://localhost:3000/dashboard/demo"
    finally:
        db.close()


def test_dedupe_summary_artifact_references_strips_duplicate_dashboard_url_from_run_outputs():
    workspace_state = {
        "run": {
            "status": "success",
            "result": {
                "outputs": {
                    "dashboard": {
                        "dashboard_url": "/dashboards/demo/",
                        "output_path": "/workspace/.workflow_scripts/dashboard",
                        "message": "ready",
                    }
                }
            },
        },
        "artifacts": [
            {
                "id": "artifact-1",
                "kind": "dashboard",
                "payload": {
                    "kind": "dashboard",
                    "dashboard_url": "/dashboards/demo/",
                    "output_path": "/workspace/.workflow_scripts/dashboard",
                },
            }
        ],
    }

    deduped = dedupe_summary_artifact_references(workspace_state)

    assert deduped["run"]["result"]["outputs"]["dashboard"]["message"] == "ready"
    assert "dashboard_url" not in deduped["run"]["result"]["outputs"]["dashboard"]
    assert "output_path" not in deduped["run"]["result"]["outputs"]["dashboard"]
    assert deduped["artifacts"][0]["payload"]["dashboard_url"] == "/dashboards/demo/"


def test_finalize_tracked_workflow_run_compacts_large_row_outputs():
    db = _build_test_db()
    try:
        user = _create_user(db, email="erin@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Analyze a large table")
        draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            turn_id=turn.id,
            file_path="/workspace/workflow/large.json",
            definition={"root": {"nodes": {"answer": {"id": "answer"}}, "edges": {}}},
        )
        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            turn_id=turn.id,
            draft_id=draft.id,
            file_path=draft.file_path,
        )

        rows = [{"city": f"City {idx}", "revenue": idx} for idx in range(50)]
        finalized = finalize_tracked_workflow_run(
            db,
            run,
            status="success",
            result={
                "status": "success",
                "outputs": {
                    "aggregate": {
                        "rows": rows,
                    }
                },
            },
            artifacts=[],
        )

        stored_rows = finalized.result["outputs"]["aggregate"]["rows"]
        assert len(stored_rows) == 20
        assert finalized.result["outputs"]["aggregate"]["row_count"] == 50
        assert finalized.result["outputs"]["aggregate"]["preview_rows"][0]["city"] == "City 0"
    finally:
        db.close()


def test_finalize_tracked_workflow_run_drops_duplicate_tabular_metadata_when_dataset_ref_exists():
    db = _build_test_db()
    try:
        user = _create_user(db, email="frank@example.com")
        session = _create_session(db, user)
        turn = create_chat_turn(db, session.id, user.id, "Analyze compact dataset outputs")
        draft = upsert_workflow_draft(
            db,
            session_id=session.id,
            user_id=user.id,
            turn_id=turn.id,
            file_path="/workspace/workflow/compact.json",
            definition={"root": {"nodes": {"sql": {"id": "sql"}}, "edges": {}}},
        )
        run = create_tracked_workflow_run(
            db,
            user_id=user.id,
            session_id=session.id,
            turn_id=turn.id,
            draft_id=draft.id,
            file_path=draft.file_path,
        )

        finalized = finalize_tracked_workflow_run(
            db,
            run,
            status="success",
            result={
                "status": "success",
                "outputs": {
                    "sql": {
                        "dataset_ref": {
                            "kind": "dataset_ref",
                            "path": "/workspace/.datasets/sql.jsonl",
                            "format": "jsonl",
                            "row_count": 50,
                            "columns": ["city", "revenue"],
                            "preview_rows": [{"city": "City 0", "revenue": 0}],
                        },
                        "row_count": 50,
                        "columns": ["city", "revenue"],
                        "preview_rows": [{"city": "City 0", "revenue": 0}],
                    }
                },
            },
            artifacts=[],
        )

        stored = finalized.result["outputs"]["sql"]
        assert "row_count" not in stored
        assert "columns" not in stored
        assert "preview_rows" not in stored
        assert stored["dataset_ref"]["row_count"] == 50
        assert stored["dataset_ref"]["columns"] == ["city", "revenue"]
        assert stored["dataset_ref"]["preview_rows"][0]["city"] == "City 0"
    finally:
        db.close()
