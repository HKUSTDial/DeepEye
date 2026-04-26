"""Tests for workflow lifecycle helpers."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.lifecycle import next_turn_status_after_run_finalized, normalize_workflow_run_status


def test_normalize_workflow_run_status_maps_legacy_aliases() -> None:
    assert normalize_workflow_run_status("pending") == "queued"
    assert normalize_workflow_run_status("started") == "running"
    assert normalize_workflow_run_status("succeeded") == "success"
    assert normalize_workflow_run_status("error") == "failed"
    assert normalize_workflow_run_status("canceled") == "cancelled"


def test_finalized_successful_run_moves_turn_to_summarizing() -> None:
    assert next_turn_status_after_run_finalized("success", "running") == "summarizing"
    assert next_turn_status_after_run_finalized("completed", "running") == "summarizing"


def test_finalized_failed_or_cancelled_run_does_not_force_summarizing() -> None:
    assert next_turn_status_after_run_finalized("failed", "running") is None
    assert next_turn_status_after_run_finalized("cancelled", "running") is None
    assert next_turn_status_after_run_finalized("success", "failed") is None
