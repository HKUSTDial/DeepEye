"""Tests for workflow artifact normalization."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.schemas.workflow_artifact import WorkflowArtifactPayload
from app.workflow.artifacts import normalize_workflow_artifact


def test_normalize_report_artifact_adds_protocol_fields_without_dropping_legacy_fields():
    artifact = normalize_workflow_artifact(
        "report",
        node_id="report_node",
        report_path="/workspace/analysis_report.html",
        report_html="<html>ok</html>",
        report_filename="analysis_report.html",
        status="success",
        message="Report ready",
    )

    assert artifact["kind"] == "report"
    assert artifact["status"] == "ready"
    assert artifact["node_id"] == "report_node"
    assert artifact["title"] == "analysis_report.html"
    assert artifact["summary"] == "Report ready"
    assert artifact["report_html"] == "<html>ok</html>"
    assert artifact["preview"] == {
        "content_key": "report_html",
        "mime_type": "text/html",
        "path": "/workspace/analysis_report.html",
        "type": "html",
    }
    assert artifact["files"] == [
        {
            "mime_type": "text/html",
            "name": "analysis_report.html",
            "path": "/workspace/analysis_report.html",
            "role": "report",
        }
    ]
    assert artifact["payload"]["report_path"] == "/workspace/analysis_report.html"


def test_normalize_video_artifact_distinguishes_running_task_from_ready_preview():
    running = normalize_workflow_artifact("video", task_id="task-1")
    ready = normalize_workflow_artifact(
        "video",
        task_id="task-1",
        video_url="/video-previews/deepeye-video-task-1/",
    )

    assert running["status"] == "running"
    assert running["preview"] == {"type": "none"}
    assert ready["status"] == "ready"
    assert ready["preview"] == {
        "type": "url",
        "url": "/video-previews/deepeye-video-task-1/",
    }
    assert ready["video_url"] == "/video-previews/deepeye-video-task-1/"


def test_normalize_table_artifact_builds_table_preview():
    artifact = normalize_workflow_artifact(
        "table",
        rows=[
            {"city": "Austin", "revenue": 10},
            {"city": "Boston", "revenue": 20},
        ],
    )

    assert artifact["status"] == "ready"
    assert artifact["preview"] == {
        "columns": ["city", "revenue"],
        "rows": [
            {"city": "Austin", "revenue": 10},
            {"city": "Boston", "revenue": 20},
        ],
        "type": "table",
    }
    assert artifact["payload"]["rows"][0]["city"] == "Austin"


def test_normalize_existing_artifact_is_idempotent():
    artifact = normalize_workflow_artifact(
        "dashboard",
        dashboard_url="/dashboards/demo/",
        payload={"custom": "value"},
        preview={"type": "iframe", "url": "/dashboards/demo/"},
    )
    normalized = normalize_workflow_artifact(artifact.get("kind"), artifact)

    assert normalized["preview"] == {"type": "iframe", "url": "/dashboards/demo/"}
    assert normalized["payload"]["custom"] == "value"
    assert normalized["payload"]["dashboard_url"] == "/dashboards/demo/"


def test_normalized_artifact_payload_matches_typed_protocol_model():
    artifact = normalize_workflow_artifact(
        "dashboard",
        node_id="dashboard_node",
        dashboard_url="/dashboards/demo/",
        status="completed",
    )
    payload = WorkflowArtifactPayload.model_validate(artifact)

    assert payload.kind == "dashboard"
    assert payload.status == "ready"
    assert payload.node_id == "dashboard_node"
    assert payload.preview.url == "/dashboards/demo/"
    assert payload.preview.type == "url"
    assert payload.payload["dashboard_url"] == "/dashboards/demo/"


def test_artifact_payload_model_accepts_legacy_payloads():
    payload = WorkflowArtifactPayload.model_validate(
        {
            "kind": "report",
            "status": "success",
            "report_path": "/workspace/legacy.html",
        }
    )

    assert payload.status == "ready"
    assert payload.title is None
    assert payload.model_dump(exclude_none=True)["report_path"] == "/workspace/legacy.html"
