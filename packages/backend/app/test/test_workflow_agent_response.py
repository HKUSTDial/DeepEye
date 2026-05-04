"""Tests for workflow agent response assembly."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.services.agent_response import build_workflow_agent_response


def test_build_workflow_agent_response_replies_directly_when_final_answer_exists() -> None:
    workspace_state = {
        "draft": {"id": "draft-1"},
        "run": {
            "id": "run-1",
            "status": "success",
            "error": None,
            "result": {"outputs": {"answer_node": {"answer": "Final grounded answer."}}},
        },
        "artifacts": [{"kind": "report"}],
    }

    response = build_workflow_agent_response(
        goal="Answer the question",
        agent_result={"messages": ["m1", "m2"]},
        turn_id="turn-1",
        terminal_failure=None,
        workspace_state=workspace_state,
    )

    assert response["status"] == "success"
    assert response["next_action"] == "reply_directly"
    assert response["final_answer"] == "Final grounded answer."
    assert response["artifacts"] == ["report"]
    assert response["message_count"] == 2


def test_build_workflow_agent_response_routes_to_summary_without_final_answer() -> None:
    workspace_state = {
        "draft": {"id": "draft-1"},
        "run": {
            "id": "run-1",
            "status": "success",
            "error": None,
            "result": {"outputs": {"report_node": {"report_url": "/reports/a.html"}}},
        },
        "artifacts": [{"kind": "report"}],
    }

    response = build_workflow_agent_response(
        goal="Build a report",
        agent_result={"messages": []},
        turn_id=None,
        terminal_failure=None,
        workspace_state=workspace_state,
    )

    assert response["status"] == "success"
    assert response["next_action"] == "summarize_workflow_result"
    assert response["final_answer"] is None


def test_build_workflow_agent_response_uses_terminal_failure_reply() -> None:
    workspace_state = {
        "draft": {"id": "draft-1"},
        "run": {"id": "run-1", "status": "failed", "error": "bad wiring", "result": {}},
        "artifacts": [],
    }
    terminal_failure = {
        "error_type": "repair_limit_exceeded",
        "error_summary": "Workflow repair limit reached for draft draft-1.",
        "error": "Workflow repair limit exceeded.",
        "issues": ["root.edges invalid"],
    }

    response = build_workflow_agent_response(
        goal="分析附加数据并回答问题",
        agent_result={"messages": ["stopped"]},
        turn_id="turn-1",
        terminal_failure=terminal_failure,
        workspace_state=workspace_state,
    )

    assert response["status"] == "failed"
    assert response["next_action"] == "reply_directly"
    assert response["draft_id"] == "draft-1"
    assert response["run_id"] == "run-1"
    assert response["issues"] == ["root.edges invalid"]
    assert "自动修复两次后仍未收敛" in response["final_answer"]
