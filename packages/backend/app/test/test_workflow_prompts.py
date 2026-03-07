"""Tests for workflow planner prompt rules."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.services.workflow_engine import build_registry
from app.services.workflow_prompts import build_workflow_prompt, render_node_specs
from deepeye.workflows.registry import NodeRegistry


def test_workflow_prompt_requires_repair_loop_on_validation_failures():
    prompt = build_workflow_prompt(NodeRegistry())

    assert "Reuse ONE workflow draft" in prompt
    assert "validation_errors" in prompt
    assert "Reuse the SAME `draft_id`" in prompt
    assert "Limit repair attempts to 2" in prompt
    assert "prefer `create_workflow_and_run`" in prompt
    assert "Do NOT call `read_workflow`, `update_workflow`, or `run_workflow` before the first run" in prompt
    assert "File + database joint analysis" in prompt
    assert "Use `datasource.read` only for attached files." in prompt
    assert "Use `sql.execute` only for attached databases." in prompt
    assert "single business answer" in prompt
    assert "run_workflow_from_file" not in prompt
    assert "rows.select" in prompt
    assert "rows.aggregate" in prompt
    assert "llm.answer" in prompt
    assert "dataset_ref" in prompt
    assert "data.get('dataset_ref', [])" in prompt
    assert "MUST include source nodes" in prompt
    assert "Do NOT create python.code-only" in prompt
    assert "Never bypass source nodes" in prompt
    assert "analysis-ready dataset" in prompt
    assert "required transform when the source is large/raw" in prompt
    assert "create_plan" not in prompt
    assert "update_plan" not in prompt


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
