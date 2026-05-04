"""Integration-style tests for dataset_ref-first workflow paths."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tarfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

import pytest
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, DataSource, User
from app.node.code.python_code import PythonCodeHandler
from app.node.dashboard.node import NL2DashboardHandler
from app.node.data.datasource_read import DataSourceReadHandler
from app.node.data.sql_execute import SqlExecuteHandler
from app.node.report.node import ReportGenerateHandler
from app.node.video.node import VideoGeneratorHandler
from app.workflow.services.datasets import materialize_rows_to_sandbox_dataset
from deepeye.workflows.models import Node


class _FakeExecResult:
    def __init__(self, exit_code: int = 0, output: bytes = b"") -> None:
        self.exit_code = exit_code
        self.output = output


class _FakeContainer:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.python_output: bytes = b"[]"
        self.last_python_input_path: str | None = None

    def _read_rows_from_file(self, path: str, fmt: str) -> list[dict[str, object]]:
        raw = self.files[path]
        if fmt == "csv":
            text = raw.decode("utf-8")
            return [dict(row) for row in csv.DictReader(io.StringIO(text))]
        if fmt == "jsonl":
            return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        raise AssertionError(f"Unsupported fake read format: {fmt}")

    def exec_run(self, cmd, demux=False, workdir=None):
        del workdir
        if isinstance(cmd, list) and cmd[:2] == ["bash", "-c"]:
            script = cmd[2]
            if script.startswith("mkdir -p "):
                if demux:
                    return 0, (b"", b"")
                return _FakeExecResult(0, b"")
            if "cat > " in script and "\n" in script:
                header, body = script.split("\n", 1)
                path = header.split("cat > ", 1)[1].split(" <<", 1)[0].strip()
                terminator = body.rsplit("\n", 1)[1]
                content = body[: -(len(terminator) + 1)]
                self.files[path] = content.encode("utf-8")
                if demux:
                    return 0, (b"", b"")
                return _FakeExecResult(0, b"")
            if "&& python " in script:
                input_path = script.split("<", 1)[1].strip() if "<" in script else None
                self.last_python_input_path = input_path
                if demux:
                    return 0, (self.python_output, b"")
                return _FakeExecResult(0, self.python_output)
            if demux:
                return 0, (b"", b"")
            return _FakeExecResult(0, b"")

        if isinstance(cmd, list) and cmd[:2] == ["python3", "-c"]:
            path = cmd[3]
            arg4 = cmd[4]
            arg5 = cmd[5]
            if str(arg4).isdigit():
                rows = self._read_rows_from_file(path, str(arg5).lower())
                rows = rows[: int(arg4)]
            else:
                rows = self._read_rows_from_file(path, str(arg4).lower())
                if arg5 != "__all__":
                    rows = rows[: int(arg5)]
            return _FakeExecResult(0, json.dumps(rows).encode("utf-8"))

        if isinstance(cmd, list) and cmd[0] == "cat":
            path = cmd[1]
            if demux:
                return 0, (self.files[path], b"")
            return _FakeExecResult(0, self.files[path])

        if isinstance(cmd, str):
            if cmd.startswith("mkdir -p "):
                return _FakeExecResult(0, b"")
            if cmd.startswith("cat "):
                path = cmd.split(" ", 1)[1].strip()
                return _FakeExecResult(0, self.files[path])

        raise AssertionError(f"Unexpected exec_run: {cmd}")

    def put_archive(self, dest_dir, fp) -> None:
        with tarfile.open(fileobj=fp, mode="r:*") as tar:
            for member in tar.getmembers():
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                self.files[f"{dest_dir.rstrip('/')}/{member.name}"] = extracted.read()


class _FakeSandbox(SimpleNamespace):
    def __init__(self, session_id: str = "session-test") -> None:
        super().__init__(container=_FakeContainer(), session_id=session_id)


def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


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


def test_file_datasource_dataset_ref_flows_to_report_and_video(tmp_path, monkeypatch) -> None:
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

        sandbox = _FakeSandbox()
        sandbox.container.files["/workspace/data/clients.csv"] = (
            b"city,revenue\nShanghai,120\nBeijing,80\nShenzhen,150\n"
        )

        ds_handler = DataSourceReadHandler(db, user.id, sandbox=sandbox)
        ds_result = ds_handler.execute(
            Node(id="read_clients", type="datasource.read", params={"datasource_id": str(datasource.id), "limit": 10}),
            {},
            context=None,
        )

        assert ds_result["dataset_ref"]["kind"] == "dataset_ref"
        assert ds_result["dataset_ref"]["row_count"] == 3

        captured_report_csvs: list[str] = []

        def _fake_run_report_pipeline(*, session_id, user_query, csv_paths, template_name, output_filename):
            del session_id, user_query, template_name, output_filename
            captured_report_csvs.extend(csv_paths)
            assert csv_paths and all(Path(path).suffix == ".csv" for path in csv_paths)
            return "<html>report</html>", None

        monkeypatch.setattr("app.node.report.node.run_report_pipeline", _fake_run_report_pipeline)
        report_handler = ReportGenerateHandler(db, str(user.id), sandbox=sandbox, session_id="session-report")
        report_result = report_handler.execute(
            Node(id="report", type="report.generate", params={"query": "Analyze revenue"}),
            {"dataset_ref": ds_result["dataset_ref"]},
            context=None,
        )

        assert report_result["report_path"].endswith("analysis_report.html")
        assert report_result["report_html"] == "<html>report</html>"
        assert captured_report_csvs

        video_handler = VideoGeneratorHandler(db, str(user.id), sandbox=sandbox)
        monkeypatch.setattr(video_handler.generator, "generate", lambda **kwargs: {"scenes": [{"id": "s1"}], "meta": {}})
        monkeypatch.setattr(video_handler, "_generate_audio_and_align", lambda config, language, task_id=None, session_id=None: {**config, "meta": {"video_duration": 6.0}})
        monkeypatch.setattr(video_handler, "_render_video", lambda config_path, workers=5, session_id=None: {"video_path": "/workspace/videos/demo", "video_info": {"status": "success", "component_count": 1}})

        video_result = video_handler.execute(
            Node(id="video", type="video.generator", params={"query": "Generate a video", "language": "Chinese"}),
            {"dataset_ref": ds_result["dataset_ref"]},
            context=None,
        )

        assert video_result["video_info"]["status"] == "success"
        assert video_result["task_id"]
    finally:
        db.close()


def test_report_handler_returns_full_html_for_panel_render(monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="report-html@example.com")
        _create_session(db, user)
        sandbox = _FakeSandbox()

        long_html = "<html>" + ("x" * 1200) + "</html>"

        def _fake_run_report_pipeline(*, session_id, user_query, csv_paths, template_name, output_filename):
            del session_id, user_query, csv_paths, template_name, output_filename
            return long_html, None

        monkeypatch.setattr("app.node.report.node.run_report_pipeline", _fake_run_report_pipeline)
        report_handler = ReportGenerateHandler(db, str(user.id), sandbox=sandbox, session_id="session-report")
        dataset_ref = materialize_rows_to_sandbox_dataset(
            [{"city": "Hangzhou", "revenue": 100}],
            sandbox=sandbox,
            name_hint="report_input",
            source="test",
        )

        report_result = report_handler.execute(
            Node(id="report", type="report.generate", params={"query": "Analyze revenue"}),
            {"dataset_ref": dataset_ref},
            context=None,
        )

        assert report_result["report_html"] == long_html
        assert len(report_result["report_html"]) > 500
    finally:
        db.close()


def test_sql_dataset_ref_flows_to_python_and_dashboard(tmp_path, monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="bob@example.com")
        sandbox = _FakeSandbox(session_id="session-dashboard")

        sqlite_path = tmp_path / "sales.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("create table sales(city text, revenue integer)")
        conn.executemany(
            "insert into sales(city, revenue) values(?, ?)",
            [("Shanghai", 120), ("Beijing", 80), ("Shenzhen", 150)],
        )
        conn.commit()
        conn.close()
        datasource = DataSource(
            user_id=user.id,
            name="sales.db",
            type="sqlite",
            category="database",
            connection_string=f"sqlite:///{sqlite_path}",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)

        sql_handler = SqlExecuteHandler(db, user.id, sandbox=sandbox)
        sql_result = sql_handler.execute(
            Node(
                id="sql_sales",
                type="sql.execute",
                params={
                    "datasource_id": str(datasource.id),
                    "query": "select city, revenue from sales order by revenue desc",
                },
            ),
            {},
            context=None,
        )

        assert sql_result["dataset_ref"]["kind"] == "dataset_ref"
        assert sql_result["dataset_ref"]["row_count"] == 3

        python_output_ref = materialize_rows_to_sandbox_dataset(
            [{"city": "Shenzhen", "top_revenue": 150}],
            sandbox=sandbox,
            name_hint="python_output",
            source="test.python",
        )
        sandbox.container.python_output = json.dumps(python_output_ref).encode("utf-8")
        python_handler = PythonCodeHandler(sandbox)
        python_result = python_handler.execute(
            Node(id="python", type="python.code", params={"code": "print('ok')"}),
            {"dataset_ref": sql_result["dataset_ref"], "input": {"metric": "top_revenue"}},
            context=None,
        )

        payload = json.loads(sandbox.container.files[sandbox.container.last_python_input_path].decode("utf-8"))
        assert payload["dataset_ref"][0]["path"] == sql_result["dataset_ref"]["path"]
        assert python_result["dataset_ref"]["kind"] == "dataset_ref"

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
        monkeypatch.setattr("app.deploy.services.dashboard.dashboard_deployer.deploy", _fake_dashboard_deploy)

        dashboard_handler = NL2DashboardHandler(db, str(user.id), sandbox=sandbox)
        dashboard_handler._emit_log = lambda *args, **kwargs: None
        dashboard_handler._emit_workflow_event = lambda *args, **kwargs: None
        dashboard_result = dashboard_handler.execute(
            Node(id="dashboard", type="data.generate_dashboard", params={"question": "Show top city revenue"}),
            {"dataset_ref": sql_result["dataset_ref"]},
            context=None,
        )

        assert dashboard_result["dashboard_url"].startswith("/dashboards/")
        assert dashboard_result["output_path"].startswith("/workspace/.workflow_scripts/")
    finally:
        db.close()


def test_dashboard_handler_emits_failure_without_ready_when_deploy_fails(monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="dashboard-fail@example.com")
        sandbox = _FakeSandbox(session_id="session-dashboard-fail")
        dataset_ref = materialize_rows_to_sandbox_dataset(
            [{"city": "Shenzhen", "revenue": 150}],
            sandbox=sandbox,
            name_hint="dashboard_input",
            source="test",
        )

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

        async def _failing_dashboard_deploy(task_id, local_va_app_path=None, source_archive_bytes=None, session_id=None):
            assert task_id == "dashboard"
            assert local_va_app_path is not None
            assert source_archive_bytes is None
            assert session_id == sandbox.session_id
            return {
                "status": "error",
                "url": f"/dashboards/deepeye-nl2dashboard-{task_id}/",
            }

        monkeypatch.setattr("app.node.dashboard.node.DashboardDesigner", _DummyDesigner)
        monkeypatch.setattr("app.node.dashboard.node.DashboardEngineer", _DummyEngineer)
        monkeypatch.setattr("app.node.dashboard.node.LLMClient", lambda api_key=None, base_url=None: object())
        monkeypatch.setattr("app.deploy.services.dashboard.dashboard_deployer.deploy", _failing_dashboard_deploy)

        dashboard_handler = NL2DashboardHandler(db, str(user.id), sandbox=sandbox)
        emitted_logs: list[tuple[str, bool]] = []
        emitted_events: list[tuple[str, dict | None, bool]] = []
        dashboard_handler._emit_log = lambda text, sync=False: emitted_logs.append((text, sync))
        dashboard_handler._emit_workflow_event = (
            lambda phase, payload=None, sync=False: emitted_events.append((phase, payload, sync))
        )

        with pytest.raises(RuntimeError, match="Dashboard deployment returned non-running status"):
            dashboard_handler.execute(
                Node(id="dashboard", type="data.generate_dashboard", params={"question": "Show top city revenue"}),
                {"dataset_ref": dataset_ref},
                context=None,
            )

        assert [phase for phase, _, _ in emitted_events] == ["artifact_failed"]
        assert any("Dashboard generation failed" in text for text, _ in emitted_logs)
        assert all("deployment complete" not in text.lower() for text, _ in emitted_logs)
    finally:
        db.close()


def test_sql_execute_materializes_preview_and_dataset_in_single_query(tmp_path, monkeypatch) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="sql-single-query@example.com")
        _create_session(db, user)
        sqlite_path = tmp_path / "sales.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("create table sales(city text, revenue integer)")
        conn.executemany(
            "insert into sales(city, revenue) values(?, ?)",
            [("Shanghai", 120), ("Beijing", 80), ("Shenzhen", 150)],
        )
        conn.commit()
        conn.close()

        engine = create_engine(f"sqlite:///{sqlite_path}")
        query_count = {"value": 0}

        @event.listens_for(engine, "before_cursor_execute")
        def _count_queries(*args, **kwargs):
            del args, kwargs
            query_count["value"] += 1

        monkeypatch.setattr("app.workflow.services.datasets.create_engine", lambda connection_string: engine)
        datasource = DataSource(
            user_id=user.id,
            name="sales.db",
            type="sqlite",
            category="database",
            connection_string=f"sqlite:///{sqlite_path}",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)

        sandbox = _FakeSandbox()
        handler = SqlExecuteHandler(db, user.id, sandbox=sandbox)
        result = handler.execute(
            Node(
                id="sql",
                type="sql.execute",
                params={
                    "datasource_id": str(datasource.id),
                    "query": "select city, revenue from sales order by revenue desc",
                    "limit": 2,
                },
            ),
            {},
            context=None,
        )

        assert query_count["value"] == 1
        assert result["dataset_ref"]["row_count"] == 3
        assert len(result["dataset_ref"]["preview_rows"]) == 2
        assert result["dataset_ref"]["path"].startswith("/workspace/.datasets/")
    finally:
        db.close()


def test_datasource_read_rejects_database_datasource(tmp_path) -> None:
    db = _build_test_db()
    try:
        user = _create_user(db, email="datasource-read-reject-db@example.com")
        _create_session(db, user)
        sqlite_path = tmp_path / "customers.db"
        conn = sqlite3.connect(sqlite_path)
        conn.execute("create table customers(city text, revenue integer)")
        conn.executemany(
            "insert into customers(city, revenue) values(?, ?)",
            [("Shanghai", 120), ("Beijing", 80), ("Shenzhen", 150)],
        )
        conn.commit()
        conn.close()
        datasource = DataSource(
            user_id=user.id,
            name="customers.db",
            type="sqlite",
            category="database",
            connection_string=f"sqlite:///{sqlite_path}",
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)

        sandbox = _FakeSandbox()
        handler = DataSourceReadHandler(db, user.id, sandbox=sandbox)
        try:
            handler.execute(
                Node(
                    id="read_db",
                    type="datasource.read",
                    params={"datasource_id": str(datasource.id), "limit": 2},
                ),
                {},
                context=None,
            )
        except ValueError as exc:
            assert "only supports file datasources" in str(exc)
        else:
            raise AssertionError("datasource.read should reject database datasources")
    finally:
        db.close()
