from app.workflow.services.engine import build_registry
from deepeye.workflows.models import Graph, Node
from deepeye.workflows.validation import validate_workflow_graph


def test_workflow_node_specs_serialize_schema_with_public_alias() -> None:
    specs = [spec.model_dump(mode="json", by_alias=True) for spec in build_registry().all()]

    assert specs
    for spec in specs:
        for port_group in ("inputs", "outputs"):
            for port in spec.get(port_group, {}).values():
                assert "schema_" not in port
                if port:
                    assert "schema" in port or not port


def test_workflow_node_specs_include_version() -> None:
    specs = build_registry().all()

    assert specs
    assert all(spec.version for spec in specs)


def test_workflow_node_specs_include_builtin_transform_and_answer_nodes() -> None:
    node_types = {spec.type for spec in build_registry().all()}

    assert {"rows.select", "rows.filter", "rows.sort", "rows.aggregate", "rows.profile", "llm.answer"} <= node_types


def test_workflow_node_specs_hide_internal_or_legacy_params() -> None:
    specs = {spec.type: spec for spec in build_registry().all()}

    assert "datasource_url" not in (specs["datasource.read"].params_schema or {})
    assert "datasource_type" not in (specs["datasource.read"].params_schema or {})
    assert "table" not in (specs["datasource.read"].params_schema or {})
    assert "query" not in (specs["datasource.read"].params_schema or {})
    assert "datasource_url" not in (specs["sql.execute"].params_schema or {})
    assert "datasource_type" not in (specs["sql.execute"].params_schema or {})
    assert "code_path" not in (specs["python.code"].params_schema or {})
    assert "code_b64" not in (specs["python.code"].params_schema or {})
    assert "workdir" not in (specs["python.code"].params_schema or {})
    assert "nulls_last" not in (specs["rows.sort"].params_schema or {})
    assert "sample_size" not in (specs["rows.profile"].params_schema or {})
    assert "file_paths" not in (specs["report.generate"].params_schema or {})
    assert "template" not in (specs["report.generate"].params_schema or {})
    assert "output_path" not in (specs["report.generate"].params_schema or {})
    assert "model" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "data" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "datasource_id" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "data_schema" not in (specs["data.generate_dashboard"].params_schema or {})
    assert "workers" not in (specs["video.generator"].params_schema or {})
    assert "instructions" not in (specs["llm.answer"].params_schema or {})
    assert "query" not in specs["sql.execute"].inputs
    assert "question" not in specs["llm.answer"].inputs
    assert "question" not in specs["data.generate_dashboard"].inputs
    assert "query" not in specs["video.generator"].inputs
    assert "preview_rows" not in specs["datasource.read"].outputs
    assert "row_count" not in specs["datasource.read"].outputs
    assert "columns" not in specs["datasource.read"].outputs
    assert "preview_rows" not in specs["sql.execute"].outputs
    assert "row_count" not in specs["sql.execute"].outputs
    assert "columns" not in specs["sql.execute"].outputs
    assert "preview_rows" not in specs["python.code"].outputs
    assert "row_count" not in specs["python.code"].outputs
    assert "columns" not in specs["python.code"].outputs
    assert "preview_rows" not in specs["rows.select"].outputs
    assert "row_count" not in specs["rows.select"].outputs
    assert "columns" not in specs["rows.select"].outputs
    assert "preview_rows" not in specs["rows.filter"].outputs
    assert "row_count" not in specs["rows.filter"].outputs
    assert "columns" not in specs["rows.filter"].outputs
    assert "preview_rows" not in specs["rows.sort"].outputs
    assert "row_count" not in specs["rows.sort"].outputs
    assert "columns" not in specs["rows.sort"].outputs
    assert "preview_rows" not in specs["rows.profile"].outputs
    assert "row_count" not in specs["rows.profile"].outputs
    assert "columns" not in specs["rows.profile"].outputs
    assert "preview_rows" not in specs["rows.aggregate"].outputs
    assert "row_count" not in specs["rows.aggregate"].outputs
    assert "columns" not in specs["rows.aggregate"].outputs
    assert "status" not in specs["report.generate"].outputs
    assert "message" not in specs["report.generate"].outputs
    assert "stdout" not in specs["python.code"].outputs
    assert "stderr" not in specs["python.code"].outputs
    assert "exit_code" not in specs["python.code"].outputs
    assert "dashboard_config" not in specs["data.generate_dashboard"].outputs
    assert "config" not in specs["video.generator"].outputs
    assert "config_path" not in specs["video.generator"].outputs


def test_workflow_validation_rejects_missing_required_params_and_inputs() -> None:
    registry = build_registry()
    graph = Graph(
        nodes={
            "read": Node(id="read", type="datasource.read"),
            "answer": Node(id="answer", type="llm.answer"),
            "dashboard": Node(id="dashboard", type="data.generate_dashboard"),
            "report": Node(id="report", type="report.generate"),
            "video": Node(id="video", type="video.generator"),
        },
        edges={},
    )

    issues = validate_workflow_graph(graph, registry=registry)

    issue_codes = {(issue.code, issue.location) for issue in issues}
    assert ("param.required.missing", "nodes.read.params.datasource_id") in issue_codes
    assert ("param.required.missing", "nodes.answer.params.question") in issue_codes
    assert ("param.required.missing", "nodes.dashboard.params.question") in issue_codes
    assert ("input.required.missing", "nodes.dashboard.inputs.dataset_ref") in issue_codes
    assert ("param.required.missing", "nodes.report.params.query") in issue_codes
    assert ("input.required.missing", "nodes.report.inputs.dataset_ref") in issue_codes
    assert ("param.required.missing", "nodes.video.params.query") in issue_codes
    assert ("input.required.missing", "nodes.video.inputs.dataset_ref") in issue_codes


def test_required_input_is_not_satisfied_by_same_named_param() -> None:
    registry = build_registry()
    graph = Graph(
        nodes={
            "report": Node(
                id="report",
                type="report.generate",
                params={
                    "query": "Build a concise report",
                    "dataset_ref": {"kind": "dataset_ref", "path": "/workspace/fake.jsonl", "format": "jsonl"},
                },
            ),
        },
        edges={},
    )

    issues = validate_workflow_graph(graph, registry=registry)

    issue_codes = {(issue.code, issue.location) for issue in issues}
    assert ("input.required.missing", "nodes.report.inputs.dataset_ref") in issue_codes
