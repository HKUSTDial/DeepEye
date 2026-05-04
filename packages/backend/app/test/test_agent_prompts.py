"""Tests for backend-owned agent prompts."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.agent.prompts import (
    build_supervisor_prompt,
    build_workflow_summary_prompt,
)


def test_supervisor_prompt_requires_summary_step():
    prompt = build_supervisor_prompt()

    assert "workflow_agent" in prompt
    assert "summarize_workflow_result" in prompt
    assert "must call `summarize_workflow_result`".lower() in prompt.lower()
    assert "final_answer" in prompt
    assert "Choose one path per turn".lower() in prompt.lower()
    assert "exactly once" in prompt
    assert "Current Plan" not in prompt


def test_workflow_summary_prompt_embeds_workspace_state():
    prompt = build_workflow_summary_prompt(
        "Analyze revenue trends",
        {
            "turn": {"status": "summarizing"},
            "run": {"status": "success", "result": {"outputs": {"report": {"status": "success"}}}},
            "artifacts": [{"kind": "report"}],
        },
    )

    assert "Analyze revenue trends" in prompt
    assert '"status": "success"' in prompt
    assert '"kind": "report"' in prompt
    assert "mention it only once" in prompt
