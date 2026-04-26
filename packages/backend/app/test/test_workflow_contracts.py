"""Tests for exported workflow contracts."""

import json
import os
from pathlib import Path

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.contracts import workflow_contract_schemas


def test_exported_workflow_artifact_contract_is_current() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    contract_path = repo_root / "packages" / "contracts" / "workflow-artifact.schema.json"

    exported = json.loads(contract_path.read_text(encoding="utf-8"))

    assert exported == workflow_contract_schemas()
