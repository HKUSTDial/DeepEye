"""Tests for workflow planner prompt rules."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.services.workflow_prompts import build_workflow_prompt
from deepeye.workflows.registry import NodeRegistry


def test_workflow_prompt_requires_repair_loop_on_validation_failures():
    prompt = build_workflow_prompt(NodeRegistry())

    assert "Reuse ONE workflow draft" in prompt
    assert "validation_errors" in prompt
    assert "Reuse the SAME `draft_id`" in prompt
    assert "Limit repair attempts to 2" in prompt
