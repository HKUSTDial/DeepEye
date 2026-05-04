"""Tests for unified workflow event helpers."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.events import build_workflow_event_data, extract_workflow_artifacts


def test_build_workflow_event_data_includes_standard_fields():
    data = build_workflow_event_data(
        "session-1",
        "artifact_ready",
        {"artifact": {"kind": "report"}},
        file_path="/workspace/workflow/report.json",
        turn_id="turn-1",
        draft_id="draft-1",
        run_id="run-1",
    )

    assert data["version"] == 3
    assert data["session_id"] == "session-1"
    assert data["turn_id"] == "turn-1"
    assert data["draft_id"] == "draft-1"
    assert data["run_id"] == "run-1"
    assert data["phase"] == "artifact_ready"
    assert data["metadata"] == {"file_path": "/workspace/workflow/report.json"}
    assert data["payload"]["artifact"] == {
        "files": [],
        "kind": "report",
        "payload": {},
        "preview": {"type": "none"},
        "status": "pending",
        "title": "Report",
    }


def test_build_workflow_event_data_normalizes_legacy_artifact_payloads():
    data = build_workflow_event_data(
        "session-1",
        "artifact_ready",
        {
            "artifact": {
                "kind": "dashboard",
                "dashboard_url": "/dashboards/demo/",
            },
            "artifacts": [
                {
                    "kind": "video",
                    "video_url": "/video-previews/demo/",
                }
            ],
        },
    )

    assert data["payload"]["artifact"]["preview"] == {
        "type": "url",
        "url": "/dashboards/demo/",
    }
    assert data["payload"]["artifact"]["payload"]["dashboard_url"] == "/dashboards/demo/"
    assert data["payload"]["artifacts"][0]["preview"] == {
        "type": "url",
        "url": "/video-previews/demo/",
    }


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
    assert artifacts[0]["status"] == "ready"
    assert artifacts[0]["preview"]["type"] == "html"
    assert artifacts[0]["payload"]["report_path"] == "/workspace/analysis_report.html"
    assert artifacts[1]["dashboard_url"] == "/dashboards/demo/"
    assert artifacts[1]["preview"] == {"type": "url", "url": "/dashboards/demo/"}
    assert artifacts[2]["task_id"] == "20260306_120000"
    assert artifacts[2]["preview"] == {
        "type": "url",
        "url": "/video-previews/deepeye-video-20260306_120000/",
    }
