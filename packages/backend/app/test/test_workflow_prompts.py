"""Tests for workflow planner prompt rules."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.services.engine import build_registry
from app.workflow.prompts import build_workflow_prompt, render_node_specs
from deepeye.workflows.registry import NodeRegistry


def test_workflow_prompt_requires_repair_loop_on_validation_failures():
    prompt = build_workflow_prompt(NodeRegistry())

    assert "# Task Description" in prompt
    assert "# Inputs" in prompt
    assert "# Instructions" in prompt
    assert "# Output Format" in prompt
    assert "connected DAG" in prompt
    assert "## Explicit Planning Notes" in prompt
    assert "produce explicit `planning_notes` in the tool payload" in prompt
    assert "which nodes are needed" in prompt
    assert "the required inputs and expected outputs of each node" in prompt
    assert "how the nodes connect through edges" in prompt
    assert "why the final graph is a connected DAG" in prompt
    assert "## Schema Continuity Rules" in prompt
    assert "Reuse ONE workflow draft" in prompt
    assert "validation_errors" in prompt
    assert "Reuse the SAME `draft_id`" in prompt
    assert "Limit repair attempts to 2" in prompt
    assert "`repairable=true`" in prompt
    assert "`repairable=false`" in prompt
    assert "`error_type`" in prompt
    assert "`error_summary`" in prompt
    assert "`issues`" in prompt
    assert "prefer `create_workflow_and_run`" in prompt
    assert "Do NOT call `read_workflow`, `update_workflow`, or `run_workflow` before the first run" in prompt
    assert "File + database joint analysis" in prompt
    assert "File at reporting grain + raw database detail" in prompt
    assert "Use `datasource.read` only for attached files." in prompt
    assert "Use `sql.execute` only for attached databases." in prompt
    assert "If a file datasource is already at the reporting grain" in prompt
    assert "`root.nodes` and `root.edges` MUST be JSON objects keyed by each item's `id`" in prompt
    assert 'NEVER emit them as arrays or lists' in prompt
    assert '"root": {"nodes": {"read_file": {' in prompt
    assert '"edges": {"edge_1": {' in prompt
    assert "Use `llm.answer` for the final user-facing text answer grounded in workflow outputs." in prompt
    assert "run_workflow_from_file" not in prompt
    assert "rows.select" in prompt
    assert "rows.aggregate" in prompt
    assert "llm.answer" in prompt
    assert "dataset_ref" in prompt
    assert "Treat schema as a contract between nodes." in prompt
    assert "Never reference file-only columns" in prompt
    assert "always use explicit `AS` aliases" in prompt
    assert "Avoid `SELECT *`" in prompt
    assert "If `sql.execute` already groups or aggregates the data" in prompt
    assert "update every downstream assumption to match the new schema" in prompt
    assert "Do not assume hidden columns or original source column names survive unchanged." in prompt
    assert "Before writing `python.code`, inspect the upstream `dataset_ref.columns` mentally" in prompt
    assert "Treat each `dataset_ref` as the authoritative schema source." in prompt
    assert "data.get('dataset_ref', [])" in prompt
    assert "load_dataset_ref(ref)" in prompt
    assert "load_dataset_refs(data)" in prompt
    assert "never treat `data['dataset_ref']` as a single dict" in prompt
    assert "Do not use legacy keys like `preview` or `preview_path`" in prompt
    assert "emit_dataframe(df)" in prompt
    assert "MUST include source nodes" in prompt
    assert "Do NOT create `python.code`-only" in prompt
    assert "Never bypass source nodes" in prompt
    assert "analysis-ready dataset" in prompt
    assert "required transform when the source is large/raw" in prompt
    assert "## Valid Workflow JSON Examples" in prompt
    assert "Preferred minimal shape: omit node-level `inputs` and `outputs` blocks" in prompt
    assert "### Example 1: Database analysis answered directly" in prompt
    assert "### Example 2: File + database analysis with python.code" in prompt
    assert "### Example 3: Transform output into a report artifact" in prompt
    assert "### Example 4: Transform output into a dashboard artifact" in prompt
    assert "### Example 5: Transform output into a video artifact" in prompt
    assert "store_daily_ops" in prompt
    assert "\"join_campaign_context\"" in prompt
    assert "\"language\": \"English\"" in prompt
    assert "\"edge_sql_to_python\"" in prompt
    assert "\"query\": \"SELECT client_id AS client_id, revenue AS revenue FROM sales\"" in prompt
    assert "Artifact nodes do not fetch attached data on their own." in prompt
    assert "determine whether the problem is missing wiring or missing upstream output" in prompt
    assert "its stdout MUST be either a JSON array of row objects or a JSON `dataset_ref` object" in prompt
    assert "The workflow must stay connected end-to-end." in prompt
    assert "Do NOT insert a second narrative `python.code` or `llm.answer` between the final tabular dataset and the artifact node." in prompt
    assert "KEEP that node and make its final line emit tabular output via `emit_dataframe(df)`" in prompt
    assert "Only remove or bypass a `python.code` node before an artifact when it is clearly narrative-only" in prompt
    assert "Narrative observations belong in the artifact node params" in prompt
    assert "\"planning_notes\": \"1) ... 2) ...\"" in prompt
    assert "`workflow_wiring_invalid`" in prompt
    assert "`workflow_artifact_input_missing`" in prompt
    assert "`workflow_dataset_input_missing`" in prompt
    assert "`workflow_dataset_output_missing`" in prompt
    assert "`workflow_sql_query_invalid`" in prompt
    assert "`workflow_python_contract_invalid`" in prompt
    assert "`workflow_python_schema_invalid`" in prompt
    assert "\"edge_python_to_report\"" in prompt
    assert "create_plan" not in prompt
    assert "update_plan" not in prompt
    assert "pd.read_csv(refs[0]['path'])" not in prompt
    assert "`data['dataset_ref']` is always a list." in prompt
    assert "The dataset_ref metadata keys are `path`, `format`, `columns`, `row_count`, and optional `preview_rows`." in prompt


def test_workflow_prompt_includes_preview_for_file_and_database_tables():
    prompt = build_workflow_prompt(
        NodeRegistry(),
        datasource=[
            {"id": "file-1", "name": "clients.csv", "type": "csv", "category": "file", "local_path": "/workspace/data/clients.csv"},
            {"id": "db-1", "name": "sales_db", "type": "postgresql", "category": "database"},
        ],
        tables=[
            {
                "datasource_name": "clients.csv",
                "name": "clients.csv",
                "kind": "file",
                "columns": [{"name": "client_id", "type": "int"}, {"name": "city", "type": "string"}],
                "preview": [{"client_id": 1, "city": "Shanghai"}, {"client_id": 2, "city": "Hangzhou"}, {"client_id": 3, "city": "Shenzhen"}],
            },
            {
                "datasource_name": "sales_db",
                "name": "sales",
                "kind": "table",
                "columns": [{"name": "client_id", "type": "INTEGER"}, {"name": "revenue", "type": "FLOAT"}],
                "preview": [{"client_id": 1, "revenue": 120.5}, {"client_id": 2, "revenue": 95.0}, {"client_id": 3, "revenue": 141.2}],
            },
        ],
    )

    assert "[clients.csv] clients.csv (file): client_id:int, city:string" in prompt
    assert "[sales_db] sales (table): client_id:INTEGER, revenue:FLOAT" in prompt
    assert "Use this id in params.datasource_id for datasource.read." in prompt
    assert "Use this id in params.datasource_id for sql.execute." in prompt
    assert "preview: [{'client_id': 1, 'city': 'Shanghai'}" in prompt
    assert "preview: [{'client_id': 1, 'revenue': 120.5}" in prompt


def test_render_node_specs_hides_internal_and_derived_outputs_from_planner() -> None:
    rendered = render_node_specs(build_registry().all())

    assert "- stdout:" not in rendered
    assert "- stderr:" not in rendered
    assert "- exit_code:" not in rendered
    assert "- dashboard_config:" not in rendered
    assert "- config:" not in rendered
    assert "- config_path:" not in rendered
