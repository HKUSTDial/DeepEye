"""Tests for unified workflow event helpers."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.services.workflow_events import build_workflow_event_data, extract_workflow_artifacts


def test_build_workflow_event_data_includes_standard_fields():
    data = build_workflow_event_data(
        "session-1",
        "artifact_ready",
        {"artifact": {"kind": "report"}},
        file_path="/workspace/workflow/report.json",
    )

    assert data["version"] == 2
    assert data["session_id"] == "session-1"
    assert data["file_path"] == "/workspace/workflow/report.json"
    assert data["phase"] == "artifact_ready"
    assert data["payload"] == {"artifact": {"kind": "report"}}


def test_extract_workflow_artifacts_from_outputs():
    outputs = {
        "report_node": {
            "report_path": "/workspace/analysis_report.html",
            "report_html": "<html>ok</html>",
        },
        "dashboard_node": {
            "dashboard_url": "/dashboards/demo/",
            "output_path": "/workspace/.workflow_scripts/dashboard_123",
        },
        "video_node": {
            "task_id": "20260306_120000",
            "video_url": "/video-previews/deepeye-video-20260306_120000/",
        },
    }

    artifacts = extract_workflow_artifacts(outputs)

    assert [artifact["kind"] for artifact in artifacts] == ["report", "dashboard", "video"]
    assert artifacts[0]["report_filename"] == "analysis_report.html"
    assert artifacts[1]["dashboard_url"] == "/dashboards/demo/"
    assert artifacts[2]["task_id"] == "20260306_120000"
