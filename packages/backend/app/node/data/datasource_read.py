from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import DataSourceRepository
from app.node.core.base import BaseNode
from app.node.core.db_utils import (
    create_engine,
    fetch_rows,
    validate_datasource_type,
    validate_table_name,
)
from app.services.datasource_specs import (
    infer_file_type,
    normalize_datasource_type,
    validate_file_type,
    workspace_data_path,
)
from app.services.workflow_datasets import (
    build_dataset_ref,
    datasource_file_dataset_ref,
    materialize_sql_query_to_sandbox_result,
)
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
        datasource_id = node.params.get("datasource_id")
        datasource_url = node.params.get("datasource_url")
        datasource_type = node.params.get("datasource_type")
        table = node.params.get("table")
        query = node.params.get("query")
        limit = int(node.params.get("limit") or 100)
        
        if not datasource_id and not datasource_url:
            raise ValueError("datasource_id or datasource_url is required")

        # 1. Handle File Datasource
        if datasource_id:
            ds = DataSourceRepository(self.db).get_by_id_and_user(datasource_id, self.user_id)
            if not ds:
                raise ValueError("datasource not found")
            
            if getattr(ds, "category", "database") == "file":
                if not self.sandbox:
                    raise RuntimeError("Sandbox not available for file datasource")
                
                # Use consistent filename extraction
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
                return {
                    "preview_rows": rows,
                    "dataset_ref": dataset_ref,
                    "row_count": dataset_ref.get("row_count", len(rows)),
                    "columns": dataset_ref.get("columns", []),
                }

            connection_string = ds.connection_string
        else:
            connection_string = datasource_url

        # 2. Handle Database Datasource
        validate_datasource_type(datasource_type)
        engine = create_engine(connection_string)
        if not query:
            if not table:
                raise ValueError("table or query is required")
            validate_table_name(str(table))
            query = f"SELECT * FROM {table} LIMIT {limit}"

        if self.sandbox:
            result = materialize_sql_query_to_sandbox_result(
                db=self.db,
                user_id=self.user_id,
                sandbox=self.sandbox,
                datasource_id=str(datasource_id) if datasource_id else None,
                datasource_url=connection_string,
                datasource_type=datasource_type,
                query=str(query),
                name_hint=f"{node.id}_rows",
                source="datasource.read",
                preview_limit=limit,
            )
            return result

        rows = fetch_rows(engine, str(query), limit)
        dataset_ref = build_dataset_ref(
            path=f"/virtual/{node.id}_rows.jsonl",
            dataset_format="jsonl",
            source="datasource.read",
            preview_rows=rows,
            row_count=len(rows),
            columns=sorted({key for row in rows for key in row.keys()}),
            name=f"{node.id}_rows",
        )
        return {
            "preview_rows": rows,
            "dataset_ref": dataset_ref,
            "row_count": dataset_ref.get("row_count"),
            "columns": dataset_ref.get("columns"),
        }


class DataSourceReadNode(BaseNode):
    node_type = "datasource.read"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Read a datasource, materialize it when needed, and return a dataset_ref plus lightweight preview metadata.",
            params_schema={
                "datasource_id": {"type": "string", "required": False, "description": "Datasource ID"},
                "datasource_url": {"type": "string", "required": False, "description": "Connection string"},
                "datasource_type": {"type": "string", "required": False, "description": "postgres | mysql | sqlite"},
                "table": {"type": "string", "required": False, "description": "Table name"},
                "query": {"type": "string", "required": False, "description": "Optional SQL query"},
                "limit": {"type": "integer", "required": False, "description": "Row limit"},
            },
            outputs={
                "preview_rows": Port(schema="list[dict]", required=False, description="Preview rows for UI and summaries."),
                "dataset_ref": Port(schema="dict", required=True, description="Reference to the materialized dataset in sandbox storage."),
                "row_count": Port(schema="int", required=True, description="Materialized row count when available."),
                "columns": Port(schema="list[string]", required=False, description="Detected dataset columns."),
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id, sandbox=None):
        return DataSourceReadHandler(db, user_id, sandbox=sandbox)
