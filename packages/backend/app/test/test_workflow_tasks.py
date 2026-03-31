from __future__ import annotations

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, DataSource, User, Workflow, WorkflowRun
from app.tasks import workflow_tasks


def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _create_user(db) -> User:
    user = User(
        email="workflow-task@example.com",
        username="workflow-task",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_run_workflow_task_syncs_referenced_file_datasources(monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db)
        datasource = DataSource(
            user_id=user.id,
            name="campaign.csv",
            type="csv",
            category="file",
            storage_path="datasource-files/test/campaign.csv",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        datasource_id = str(datasource.id)

        workflow = Workflow(
            user_id=user.id,
            name="Retail manual workflow",
            description="",
            definition={
                "root": {
                    "nodes": {
                        "read_campaign": {
                            "id": "read_campaign",
                            "type": "datasource.read",
                            "params": {"datasource_id": datasource_id, "limit": 20},
                        },
                        "answer": {
                            "id": "answer",
                            "type": "llm.answer",
                            "params": {"question": "summarize"},
                        },
                    },
                    "edges": {},
                }
            },
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        run = WorkflowRun(
            workflow_id=workflow.id,
            user_id=user.id,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        sync_calls: list[tuple[str, list[str]]] = []

        async def _fake_get_or_create_sandbox(session_key: str):
            return {"session_key": session_key}

        async def _fake_sync_datasource_files(session_key: str, datasources: list[DataSource]) -> None:
            sync_calls.append((session_key, [str(item.id) for item in datasources]))

        monkeypatch.setattr(workflow_tasks, "open_task_session", lambda: db)
        monkeypatch.setattr(workflow_tasks, "_publish_run", lambda run: None)
        monkeypatch.setattr(workflow_tasks, "_publish_node", lambda run, node_id, node_status, outputs=None: None)
        monkeypatch.setattr(workflow_tasks.sandbox_manager, "get_or_create_sandbox", _fake_get_or_create_sandbox)
        monkeypatch.setattr(workflow_tasks.sandbox_manager, "sync_datasource_files", _fake_sync_datasource_files)
        monkeypatch.setattr(
            workflow_tasks,
            "run_workflow",
            lambda db, workflow, user_id, sandbox=None, on_node_start=None, on_node_end=None: {
                "status": "success",
                "runs": {},
            },
        )

        result = workflow_tasks.run_workflow_task.run(str(run.id))

        assert result["status"] == "finished"
        assert sync_calls == [(str(run.id), [datasource_id])]
    finally:
        db.close()
