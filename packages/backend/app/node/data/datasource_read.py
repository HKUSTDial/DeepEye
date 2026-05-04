from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import DataSourceRepository
from app.node.core.base import BaseNode
from app.datasource.services.specs import (
    infer_file_type,
    normalize_datasource_type,
    validate_file_type,
    workspace_data_path,
)
from app.workflow.services.datasets import datasource_file_dataset_ref
from app.sandbox.docker_sandbox import DockerSandbox
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec

_READ_FILE_SCRIPT = """
import sys
import pandas as pd

path = sys.argv[1]
limit = int(sys.argv[2])
file_type = sys.argv[3].lower()

if file_type == "csv":
    df = pd.read_csv(path, nrows=limit)
elif file_type in ("xlsx", "xls"):
    df = pd.read_excel(path, nrows=limit)
elif file_type == "json":
    try:
        df = pd.read_json(path, lines=True, nrows=limit)
    except ValueError:
        df = pd.read_json(path)
elif file_type == "parquet":
    df = pd.read_parquet(path).head(limit)
else:
    raise ValueError(f"Unsupported file type: {file_type}")

print(df.to_json(orient="records"))
"""


class DataSourceReadHandler:
    def __init__(self, db: Session, user_id, sandbox: DockerSandbox | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del inputs, context
        datasource_id = node.params.get("datasource_id")
        limit = int(node.params.get("limit") or 100)

        if not datasource_id:
            raise ValueError("datasource_id is required")

        ds = DataSourceRepository(self.db).get_by_id_and_user(datasource_id, self.user_id)
        if not ds:
            raise ValueError("datasource not found")
        if getattr(ds, "category", "database") != "file":
            raise ValueError("datasource.read only supports file datasources; use sql.execute for database datasources")
        if not self.sandbox:
            raise RuntimeError("Sandbox not available for file datasource")

        from app.sandbox.manager import _get_datasource_filename

        original_filename = _get_datasource_filename(ds)
        local_path = workspace_data_path(original_filename)
        ext_candidates = [
            getattr(ds, "type", ""),
            infer_file_type(getattr(ds, "name", "")),
            infer_file_type(original_filename),
        ]
        ext = ""
        for candidate in ext_candidates:
            try:
                validate_file_type(candidate)
                ext = normalize_datasource_type(candidate)
                break
            except ValueError:
                continue
        if not ext:
            raise ValueError("Unsupported file type")

        result = self.sandbox.container.exec_run(
            cmd=["python3", "-c", _READ_FILE_SCRIPT, local_path, str(limit), ext],
            workdir="/workspace"
        )
        if result.exit_code != 0:
            err = (result.output or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"Failed to read file in sandbox: {err}")

        payload = (result.output or b"[]").decode("utf-8", errors="replace")
        rows = json.loads(payload)
        if not isinstance(rows, list):
            raise RuntimeError("Failed to parse file rows: expected JSON array")
        dataset_ref = datasource_file_dataset_ref(datasource=ds, preview_rows=rows)
        return {"dataset_ref": dataset_ref}


class DataSourceReadNode(BaseNode):
    node_type = "datasource.read"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Load one attached file datasource into the workflow and return a dataset_ref.",
            params_schema={
                "datasource_id": {"type": "string", "required": True, "description": "Attached file datasource id to read. Use the datasource id from prompt context."},
                "limit": {"type": "integer", "required": False, "description": "Preview row limit stored inside the returned `dataset_ref`. Defaults to 100."},
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Reference to the materialized dataset for downstream nodes. Preview rows and detected columns live inside this object."),
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id, sandbox=None):
        return DataSourceReadHandler(db, user_id, sandbox=sandbox)
