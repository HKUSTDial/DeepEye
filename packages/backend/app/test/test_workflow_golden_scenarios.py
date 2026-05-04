"""Golden scenario regressions for workflow-native dataset_ref execution."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from langchain_core.messages import AIMessage

from app.models import DataSource
from app.workflow.services.datasets import materialize_rows_to_sandbox_dataset
from app.workflow.services.engine import build_engine
from app.test.test_workflow_dataset_ref_integration import (
    _FakeSandbox,
    _build_test_db,
    _create_session,
    _create_user,
)
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Workflow


class _InspectableFakeModel:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content=self.answer)


def test_golden_file_profile_workflow_answers_with_grounded_context() -> None:
    db = _build_test_db()
    try:
        user = _create_user(db)
        _create_session(db, user)
        datasource = DataSource(
            user_id=user.id,
            name="clients.csv",
            type="csv",
            category="file",
            storage_path="clients.csv",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)

        sandbox = _FakeSandbox(session_id="golden-file-answer")
        sandbox.container.files["/workspace/data/clients.csv"] = (
            b"city,revenue,segment\nShanghai,120,A\nBeijing,80,B\nShenzhen,150,A\n"
        )
        model = _InspectableFakeModel("Shenzhen has the highest revenue.")
        engine = build_engine(db, user.id, sandbox=sandbox, session_id=sandbox.session_id, model=model)

        workflow = Workflow(
            id="golden-file-profile-answer",
            root=Graph(
                nodes={
                    "read": Node(
                        id="read",
                        type="datasource.read",
                        params={"datasource_id": str(datasource.id), "limit": 20},
                    ),
                    "profile": Node(
                        id="profile",
                        type="rows.profile",
                        params={"sample_size": 3},
                    ),
                    "answer": Node(
                        id="answer",
                        type="llm.answer",
                        params={"question": "Which city has the highest revenue?"},
                    ),
                },
                edges={
                    "e1": Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="read", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="profile", port_id="dataset_ref"),
                    ),
                    "e2": Edge(
                        id="e2",
                        source=EdgeEndpoint(node_id="read", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="answer", port_id="dataset_ref"),
                    ),
                    "e3": Edge(
                        id="e3",
                        source=EdgeEndpoint(node_id="profile", port_id="profile"),
                        target=EdgeEndpoint(node_id="answer", port_id="context"),
                    ),
                },
            ),
        )

        context = engine.run(workflow)

        assert context.status == "success"
        assert context.runs["read"].outputs["dataset_ref"]["row_count"] == 3
        assert context.runs["profile"].outputs["profile"]["column_count"] == 3
        assert context.runs["answer"].outputs["answer"] == "Shenzhen has the highest revenue."
        assert model.messages is not None
        assert "Shenzhen" in model.messages[1].content
        assert '"column_count": 3' in model.messages[1].content
    finally:
        db.close()


def test_golden_cross_source_python_analysis_feeds_report_and_video(tmp_path, monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="golden-cross-source@example.com")
        _create_session(db, user)
        datasource = DataSource(
            user_id=user.id,
            name="clients.csv",
            type="csv",
            category="file",
            storage_path="clients.csv",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)

        sandbox = _FakeSandbox(session_id="golden-cross-source")
        sandbox.container.files["/workspace/data/clients.csv"] = (
            b"client_id,city\n1,Shanghai\n2,Beijing\n3,Shenzhen\n"
        )

        sqlite_path = tmp_path / "sales.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("create table sales(client_id integer, revenue integer)")
        conn.executemany(
            "insert into sales(client_id, revenue) values(?, ?)",
            [(1, 120), (2, 80), (3, 150)],
        )
        conn.commit()
        conn.close()
        sales_datasource = DataSource(
            user_id=user.id,
            name="sales.db",
            type="sqlite",
            category="database",
            connection_string=f"sqlite:///{sqlite_path}",
        )
        db.add(sales_datasource)
        db.commit()
        db.refresh(sales_datasource)

        merged_dataset_ref = materialize_rows_to_sandbox_dataset(
            [
                {"client_id": 1, "city": "Shanghai", "revenue": 120},
                {"client_id": 2, "city": "Beijing", "revenue": 80},
                {"client_id": 3, "city": "Shenzhen", "revenue": 150},
            ],
            sandbox=sandbox,
            name_hint="merged_sales_clients",
            source="golden.python",
        )
        sandbox.container.python_output = json.dumps(merged_dataset_ref).encode("utf-8")

        captured_report_csvs: list[str] = []

        def _fake_run_report_pipeline(*, session_id, user_query, csv_paths, template_name, output_filename):
            del session_id, user_query, template_name, output_filename
            captured_report_csvs.extend(csv_paths)
            return "<html>report</html>", None

        class _DummyVideoGenerator:
            def generate(self, **kwargs):
                assert kwargs["query"] == "Create a video about top client revenue"
                assert kwargs["data"]
                return {"scenes": [{"id": "scene_1"}], "meta": {}}

        monkeypatch.setattr("app.node.report.node.run_report_pipeline", _fake_run_report_pipeline)
        monkeypatch.setattr("app.node.video.node.create_generator", lambda: _DummyVideoGenerator())
        monkeypatch.setattr(
            "app.node.video.node.VideoGeneratorHandler._generate_audio_and_align",
            lambda self, config, language, task_id=None, session_id=None: {**config, "meta": {"video_duration": 4.0}},
        )
        monkeypatch.setattr(
            "app.node.video.node.VideoGeneratorHandler._render_video",
            lambda self, config_path, workers=5, session_id=None: {
                "video_path": "/workspace/videos/demo",
                "video_info": {"status": "success", "component_count": 1},
            },
        )

        engine = build_engine(db, user.id, sandbox=sandbox, session_id=sandbox.session_id)
        workflow = Workflow(
            id="golden-cross-source-artifacts",
            root=Graph(
                nodes={
                    "file": Node(
                        id="file",
                        type="datasource.read",
                        params={"datasource_id": str(datasource.id), "limit": 20},
                    ),
                    "sql": Node(
                        id="sql",
                        type="sql.execute",
                        params={
                            "datasource_id": str(sales_datasource.id),
                            "query": "select client_id, revenue from sales order by revenue desc",
                        },
                    ),
                    "python": Node(
                        id="python",
                        type="python.code",
                        params={
                            "code": (
                                "import json, sys\n"
                                "data = json.load(sys.stdin)\n"
                                "assert len(data.get(\"dataset_ref\", [])) == 2\n"
                                "print(\"ok\")\n"
                            )
                        },
                    ),
                    "report": Node(
                        id="report",
                        type="report.generate",
                        params={"query": "Create a report about top client revenue"},
                    ),
                    "video": Node(
                        id="video",
                        type="video.generator",
                        params={"query": "Create a video about top client revenue", "language": "English"},
                    ),
                },
                edges={
                    "e1": Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="file", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="python", port_id="dataset_ref"),
                    ),
                    "e2": Edge(
                        id="e2",
                        source=EdgeEndpoint(node_id="sql", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="python", port_id="dataset_ref"),
                    ),
                    "e3": Edge(
                        id="e3",
                        source=EdgeEndpoint(node_id="python", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="report", port_id="dataset_ref"),
                    ),
                    "e4": Edge(
                        id="e4",
                        source=EdgeEndpoint(node_id="python", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="video", port_id="dataset_ref"),
                    ),
                },
            ),
        )

        context = engine.run(workflow)

        assert context.status == "success"
        assert sandbox.container.last_python_input_path is not None
        payload = json.loads(sandbox.container.files[sandbox.container.last_python_input_path].decode("utf-8"))
        assert len(payload["dataset_ref"]) == 2
        assert captured_report_csvs and all(Path(path).suffix == ".csv" for path in captured_report_csvs)
        assert context.runs["report"].outputs["report_path"].endswith("analysis_report.html")
        assert context.runs["video"].outputs["video_info"]["status"] == "success"
    finally:
        db.close()


def test_golden_sql_to_dashboard_workflow(tmp_path, monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="golden-dashboard@example.com")
        sandbox = _FakeSandbox(session_id="golden-dashboard")

        sqlite_path = tmp_path / "sales.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("create table sales(city text, revenue integer)")
        conn.executemany(
            "insert into sales(city, revenue) values(?, ?)",
            [("Shanghai", 120), ("Beijing", 80), ("Shenzhen", 150)],
        )
        conn.commit()
        conn.close()
        sales_datasource = DataSource(
            user_id=user.id,
            name="sales.db",
            type="sqlite",
            category="database",
            connection_string=f"sqlite:///{sqlite_path}",
        )
        db.add(sales_datasource)
        db.commit()
        db.refresh(sales_datasource)

        class _DummyDesigner:
            def __init__(self, llm_client=None, model=None) -> None:
                del llm_client, model

            def design(self, info_doc, output_dir, callback=None):
                assert info_doc["dataset_path"].endswith(".csv")
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                if callback:
                    callback("design ok")
                return {"charts": [{"type": "bar"}]}

        class _DummyEngineer:
            def __init__(self, llm_client=None, model=None) -> None:
                del llm_client, model

            def implement(self, design_result, output_path, info_doc):
                del design_result, info_doc
                va_app = Path(output_path) / "va_app"
                va_app.mkdir(parents=True, exist_ok=True)
                (va_app / "index.html").write_text("<html>dashboard</html>")
                return str(va_app)

        async def _fake_dashboard_deploy(task_id, local_va_app_path=None, source_archive_bytes=None, session_id=None):
            assert task_id == "dashboard"
            assert local_va_app_path is not None
            assert Path(local_va_app_path).name == "va_app"
            assert source_archive_bytes is None
            assert session_id == sandbox.session_id
            return {
                "status": "running",
                "url": f"/dashboards/deepeye-nl2dashboard-{task_id}/",
            }

        monkeypatch.setattr("app.node.dashboard.node.DashboardDesigner", _DummyDesigner)
        monkeypatch.setattr("app.node.dashboard.node.DashboardEngineer", _DummyEngineer)
        monkeypatch.setattr("app.node.dashboard.node.LLMClient", lambda api_key=None, base_url=None: object())
        monkeypatch.setattr("app.node.dashboard.node.NL2DashboardHandler._emit_log", lambda self, *args, **kwargs: None)
        monkeypatch.setattr(
            "app.node.dashboard.node.NL2DashboardHandler._emit_workflow_event",
            lambda self, *args, **kwargs: None,
        )
        monkeypatch.setattr("app.deploy.services.dashboard.dashboard_deployer.deploy", _fake_dashboard_deploy)

        engine = build_engine(db, user.id, sandbox=sandbox, session_id=sandbox.session_id)
        workflow = Workflow(
            id="golden-sql-dashboard",
            root=Graph(
                nodes={
                    "sql": Node(
                        id="sql",
                        type="sql.execute",
                        params={
                            "datasource_id": str(sales_datasource.id),
                            "query": "select city, revenue from sales order by revenue desc",
                        },
                    ),
                    "dashboard": Node(
                        id="dashboard",
                        type="data.generate_dashboard",
                        params={"question": "Show top city revenue"},
                    ),
                },
                edges={
                    "e1": Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="sql", port_id="dataset_ref"),
                        target=EdgeEndpoint(node_id="dashboard", port_id="dataset_ref"),
                    ),
                },
            ),
        )

        context = engine.run(workflow)

        assert context.status == "success"
        assert context.runs["dashboard"].outputs["dashboard_url"].startswith("/dashboards/")
        assert context.runs["dashboard"].outputs["output_path"].startswith("/workspace/.workflow_scripts/")
    finally:
        db.close()
