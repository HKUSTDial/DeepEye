"""Tests for builtin workflow transform and answer nodes."""

import io
import os
import json
import tarfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from langchain_core.messages import AIMessage

from app.node.code.python_code import PythonCodeHandler
from app.workflow.services.engine import build_engine
from app.node.llm.answer import LLMAnswerHandler
from app.node.rows.basic import (
    RowsAggregateHandler,
    RowsFilterHandler,
    RowsProfileHandler,
    RowsSelectHandler,
    RowsSortHandler,
)
from app.workflow.services.datasets import dataset_ref_preview, materialize_rows_to_sandbox_dataset
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Port, Workflow
from deepeye.workflows.registry import NodeSpec


class _FakeModel:
    def __init__(self) -> None:
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content="Grounded answer.")


class _RowsSourceHandler:
    def __init__(self, sandbox) -> None:
        self.sandbox = sandbox

    def execute(self, node: Node, inputs, context):
        del inputs, context
        return {
            "dataset_ref": materialize_rows_to_sandbox_dataset(
                [
                    {"segment": "A", "revenue": 120},
                    {"segment": "A", "revenue": 150},
                    {"segment": "B", "revenue": 80},
                ],
                sandbox=self.sandbox,
                name_hint=f"{node.id}_source",
                source="test.rows.source",
            )
        }


class _FakeExecResult:
    def __init__(self, exit_code: int = 0, output: bytes = b"") -> None:
        self.exit_code = exit_code
        self.output = output


class _FakeContainer:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.python_output: bytes = b"[]"
        self.last_python_input_path: str | None = None
        self.last_python_script_path: str | None = None

    def exec_run(self, cmd, demux=False, workdir=None):
        del workdir
        if isinstance(cmd, list) and cmd[:2] == ["bash", "-c"]:
            script = cmd[2]
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
                script_path = script.split("&& python ", 1)[1].split("<", 1)[0].strip()
                self.last_python_input_path = input_path
                self.last_python_script_path = script_path
                if demux:
                    return 0, (self.python_output, b"")
                return _FakeExecResult(0, self.python_output)
            if demux:
                return 0, (b"", b"")
            return _FakeExecResult(0, b"")
        if isinstance(cmd, list) and cmd[:2] == ["python3", "-c"]:
            path = cmd[3]
            limit_raw = cmd[5]
            raw = self.files[path].decode("utf-8")
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            if limit_raw != "__all__":
                rows = rows[: int(limit_raw)]
            return _FakeExecResult(0, json.dumps(rows).encode("utf-8"))
        raise AssertionError(f"Unexpected exec_run: {cmd}")

    def put_archive(self, dest_dir, fp) -> None:
        with tarfile.open(fileobj=fp, mode="r:*") as tar:
            for member in tar.getmembers():
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                self.files[f"{dest_dir.rstrip('/')}/{member.name}"] = extracted.read()


class _FakeSandbox(SimpleNamespace):
    def __init__(self) -> None:
        super().__init__(container=_FakeContainer())


def _dataset_ref_from_rows(sandbox: _FakeSandbox, rows: list[dict[str, object]], *, name_hint: str = "input") -> dict[str, object]:
    return materialize_rows_to_sandbox_dataset(
        rows,
        sandbox=sandbox,
        name_hint=name_hint,
        source="test",
    )


def test_rows_select_filter_sort_and_profile_handlers() -> None:
    sandbox = _FakeSandbox()
    rows = [
        {"city": "Shanghai", "revenue": 120, "segment": "A"},
        {"city": "Beijing", "revenue": 80, "segment": "B"},
        {"city": "Shenzhen", "revenue": 150, "segment": "A"},
    ]
    dataset_ref = _dataset_ref_from_rows(sandbox, rows, name_hint="cities")

    selected = RowsSelectHandler(sandbox=sandbox).execute(
        Node(id="select", type="rows.select", params={"columns": ["city", "revenue"]}),
        {"dataset_ref": dataset_ref},
        context=None,
    )
    assert dataset_ref_preview(selected["dataset_ref"]) == [
        {"city": "Shanghai", "revenue": 120},
        {"city": "Beijing", "revenue": 80},
        {"city": "Shenzhen", "revenue": 150},
    ]

    filtered = RowsFilterHandler(sandbox=sandbox).execute(
        Node(id="filter", type="rows.filter", params={"column": "segment", "operator": "eq", "value": "A"}),
        {"dataset_ref": dataset_ref},
        context=None,
    )
    assert [row["city"] for row in dataset_ref_preview(filtered["dataset_ref"])] == ["Shanghai", "Shenzhen"]

    sorted_rows = RowsSortHandler(sandbox=sandbox).execute(
        Node(id="sort", type="rows.sort", params={"column": "revenue", "descending": True}),
        {"dataset_ref": dataset_ref},
        context=None,
    )
    assert [row["city"] for row in dataset_ref_preview(sorted_rows["dataset_ref"])] == ["Shenzhen", "Shanghai", "Beijing"]

    profile = RowsProfileHandler(sandbox=sandbox).execute(
        Node(id="profile", type="rows.profile", params={"sample_size": 2}),
        {"dataset_ref": dataset_ref},
        context=None,
    )
    assert profile["dataset_ref"]["row_count"] == 3
    assert profile["profile"]["column_count"] == 3
    revenue_profile = next(column for column in profile["profile"]["columns"] if column["name"] == "revenue")
    assert revenue_profile["numeric_summary"]["max"] == 150

    aggregated = RowsAggregateHandler(sandbox=sandbox).execute(
        Node(
            id="aggregate",
            type="rows.aggregate",
            params={
                "group_by": ["segment"],
                "metrics": [
                    {"column": "revenue", "op": "sum", "as": "total_revenue"},
                    {"column": "revenue", "op": "avg", "as": "avg_revenue"},
                    {"column": "city", "op": "count", "as": "row_count"},
                ],
            },
        ),
        {"dataset_ref": dataset_ref},
        context=None,
    )
    assert dataset_ref_preview(aggregated["dataset_ref"]) == [
        {"segment": "A", "total_revenue": 270, "avg_revenue": 135.0, "row_count": 2},
        {"segment": "B", "total_revenue": 80, "avg_revenue": 80.0, "row_count": 1},
    ]


def test_llm_answer_handler_uses_grounded_payload() -> None:
    model = _FakeModel()
    handler = LLMAnswerHandler(model=model)

    result = handler.execute(
        Node(id="answer", type="llm.answer", params={"question": "哪个城市收入最高？"}),
        {
            "dataset_ref": {
                "kind": "dataset_ref",
                "path": "/workspace/.datasets/cities.jsonl",
                "format": "jsonl",
                "row_count": 1,
                "preview_rows": [{"city": "Shenzhen", "revenue": 150}],
                "columns": ["city", "revenue"],
            },
            "context": [{"profile": {"row_count": 1}}],
            "artifacts": [{"kind": "report", "report_path": "/workspace/report.html"}],
        },
        context=None,
    )

    assert result["answer"] == "Grounded answer."
    assert model.messages is not None
    assert "哪个城市收入最高" in model.messages[1].content
    assert "Shenzhen" in model.messages[1].content


def test_python_code_handler_raises_on_script_failure() -> None:
    sandbox = _FakeSandbox()

    def _failing_exec_run(cmd, demux=False, workdir=None):
        if isinstance(cmd, list) and cmd[:2] == ["bash", "-c"] and "&& python " in cmd[2]:
            if demux:
                return 1, (b"", b"boom")
            return _FakeExecResult(1, b"boom")
        return sandbox.container.__class__.exec_run(sandbox.container, cmd, demux=demux, workdir=workdir)

    sandbox.container.exec_run = _failing_exec_run
    handler = PythonCodeHandler(sandbox)

    try:
        handler.execute(
            Node(id="py_fail", type="python.code", params={"code": "raise SystemExit(1)"}),
            {"input": {"task": "fail-fast"}},
            context=None,
        )
    except RuntimeError as exc:
        assert "INPUT_PREVIEW" in str(exc)
    else:
        raise AssertionError("python.code should raise on non-zero exit code")


def test_rows_handlers_accept_dataset_ref_inputs() -> None:
    sandbox = _FakeSandbox()
    rows = [{"city": f"City {idx}", "revenue": idx, "segment": "A" if idx % 2 == 0 else "B"} for idx in range(30)]
    dataset_ref = _dataset_ref_from_rows(sandbox, rows, name_hint="rows_input")

    selected = RowsSelectHandler(sandbox=sandbox).execute(
        Node(id="select", type="rows.select", params={"columns": ["city", "revenue"]}),
        {"dataset_ref": dataset_ref},
        context=None,
    )

    assert selected["dataset_ref"]["row_count"] == 30
    assert len(selected["dataset_ref"]["preview_rows"]) == 20
    assert selected["dataset_ref"]["preview_rows"][0] == {"city": "City 0", "revenue": 0}
    assert selected["dataset_ref"]["kind"] == "dataset_ref"


def test_python_code_handler_passes_dataset_refs_instead_of_full_rows() -> None:
    sandbox = _FakeSandbox()
    sandbox.container.python_output = json.dumps([{"segment": "A", "total_revenue": 270}]).encode("utf-8")
    handler = PythonCodeHandler(sandbox)
    dataset_ref = _dataset_ref_from_rows(
        sandbox,
        [{"city": f"City {idx}", "revenue": idx} for idx in range(30)],
        name_hint="py_input",
    )

    result = handler.execute(
        Node(id="py_join", type="python.code", params={"code": "print('ok')"}),
        {
            "dataset_ref": dataset_ref,
            "input": {"metric": "sum", "question": "汇总收入"},
        },
        context=None,
    )

    assert sandbox.container.last_python_input_path is not None
    payload = json.loads(sandbox.container.files[sandbox.container.last_python_input_path].decode("utf-8"))
    assert "rows" not in payload
    assert payload["input"] == {"metric": "sum", "question": "汇总收入"}
    assert isinstance(payload["dataset_ref"], list)
    assert payload["dataset_ref"][0]["kind"] == "dataset_ref"
    assert payload["dataset_ref"][0]["row_count"] == 30
    assert result["dataset_ref"]["row_count"] == 1
    assert result["dataset_ref"]["kind"] == "dataset_ref"
    assert sandbox.container.last_python_script_path is not None
    script = sandbox.container.files[sandbox.container.last_python_script_path].decode("utf-8")
    assert "def load_dataset_ref(ref):" in script
    assert "def load_dataset_refs(data):" in script
    assert "def emit_dataframe(df):" in script


def test_python_code_helper_load_dataset_ref_accepts_singleton_list(tmp_path) -> None:
    csv_path = Path(tmp_path) / "cities.csv"
    csv_path.write_text("city,revenue\nShanghai,120\n", encoding="utf-8")

    handler = PythonCodeHandler(sandbox=None)
    namespace: dict[str, object] = {}
    exec(handler._helper_prelude(), namespace)

    df = namespace["load_dataset_ref"](
        [
            {
                "kind": "dataset_ref",
                "path": str(csv_path),
                "format": "csv",
            }
        ]
    )

    assert list(df.columns) == ["city", "revenue"]
    assert df.to_dict(orient="records") == [{"city": "Shanghai", "revenue": 120}]


def test_python_code_helper_emit_json_serializes_pandas_timestamps() -> None:
    handler = PythonCodeHandler(sandbox=None)
    namespace: dict[str, object] = {}
    exec(handler._helper_prelude(), namespace)

    output = io.StringIO()
    with redirect_stdout(output):
        namespace["emit_json"](
            {
                "week_start": namespace["pd"].Timestamp("2025-10-06T00:00:00"),
                "window_end": namespace["pd"].Timestamp("2025-10-12T23:59:59"),
            }
        )

    assert json.loads(output.getvalue()) == {
        "week_start": "2025-10-06T00:00:00",
        "window_end": "2025-10-12T23:59:59",
    }


def test_workflow_engine_runs_rows_pipeline_with_llm_answer() -> None:
    model = _FakeModel()
    sandbox = _FakeSandbox()
    engine = build_engine(db=None, user_id=None, sandbox=sandbox, model=model)
    engine.node_registry.register(
        NodeSpec(
            type="rows.source",
            outputs={"dataset_ref": Port(schema="dict", required=True)},
        )
    )
    engine.register_handler("rows.source", _RowsSourceHandler(sandbox))

    workflow = Workflow(
        id="wf_rows_answer",
        root=Graph(
            nodes={
                "source": Node(id="source", type="rows.source"),
                "filter": Node(
                    id="filter",
                    type="rows.filter",
                    params={"column": "segment", "operator": "eq", "value": "A"},
                ),
                "aggregate": Node(
                    id="aggregate",
                    type="rows.aggregate",
                    params={"metrics": [{"column": "revenue", "op": "sum", "as": "total_revenue"}]},
                ),
                "answer": Node(
                    id="answer",
                    type="llm.answer",
                    params={"question": "A 分组的总收入是多少？"},
                ),
            },
            edges={
                "e1": Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="source", port_id="dataset_ref"),
                    target=EdgeEndpoint(node_id="filter", port_id="dataset_ref"),
                ),
                "e2": Edge(
                    id="e2",
                    source=EdgeEndpoint(node_id="filter", port_id="dataset_ref"),
                    target=EdgeEndpoint(node_id="aggregate", port_id="dataset_ref"),
                ),
                "e3": Edge(
                    id="e3",
                    source=EdgeEndpoint(node_id="aggregate", port_id="dataset_ref"),
                    target=EdgeEndpoint(node_id="answer", port_id="dataset_ref"),
                ),
            },
        ),
    )

    context = engine.run(workflow)

    assert context.status == "success"
    assert context.runs["aggregate"].outputs["dataset_ref"]["kind"] == "dataset_ref"
    assert context.runs["aggregate"].outputs["dataset_ref"]["preview_rows"] == [{"total_revenue": 270}]
    assert context.runs["answer"].outputs["answer"] == "Grounded answer."
