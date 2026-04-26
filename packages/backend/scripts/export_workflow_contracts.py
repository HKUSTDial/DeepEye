"""Export workflow contract schemas for frontend and integration checks."""

from __future__ import annotations

import json
from pathlib import Path

from app.workflow.contracts import workflow_contract_schemas


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output_path = repo_root / "packages" / "contracts" / "workflow-artifact.schema.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(workflow_contract_schemas(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
