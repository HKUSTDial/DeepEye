from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import DataSourceRepository
from app.node.core.base import BaseNode
from app.node.core.db_utils import create_engine, fetch_rows, validate_datasource_type
from app.services.workflow_datasets import build_dataset_ref, materialize_sql_query_to_sandbox_result
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class SqlExecuteHandler:
    def __init__(self, db: Session, user_id, sandbox=None) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        datasource_id = node.params.get("datasource_id")
        datasource_url = node.params.get("datasource_url")
        datasource_type = node.params.get("datasource_type")
        query = inputs.get("query") or node.params.get("query")
        limit = int(node.params.get("limit") or 500)
        if not query:
            raise ValueError("query is required")
        if not datasource_id and not datasource_url:
            raise ValueError("datasource_url is required")
        validate_datasource_type(datasource_type)

        connection_string = datasource_url
        if datasource_id:
            ds = DataSourceRepository(self.db).get_by_id_and_user(datasource_id, self.user_id)
            if not ds:
                raise ValueError("datasource not found")
            connection_string = ds.connection_string

        engine = create_engine(connection_string)
        if self.sandbox:
            result = materialize_sql_query_to_sandbox_result(
                db=self.db,
                user_id=self.user_id,
                sandbox=self.sandbox,
                datasource_id=str(datasource_id) if datasource_id else None,
                datasource_url=connection_string,
                datasource_type=datasource_type,
                query=str(query),
                name_hint=f"{node.id}_query",
                source="sql.execute",
                preview_limit=limit,
            )
            return result

        rows = fetch_rows(engine, str(query), limit)
        dataset_ref = build_dataset_ref(
            path=f"/virtual/{node.id}_query.jsonl",
            dataset_format="jsonl",
            source="sql.execute",
            preview_rows=rows,
            row_count=len(rows),
            columns=sorted({key for row in rows for key in row.keys()}),
            name=f"{node.id}_query",
        )
        return {
            "preview_rows": rows,
            "dataset_ref": dataset_ref,
            "row_count": dataset_ref.get("row_count"),
            "columns": dataset_ref.get("columns"),
        }


class SqlExecuteNode(BaseNode):
    node_type = "sql.execute"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Execute SQL, materialize the result, and return a dataset_ref plus lightweight preview metadata.",
            params_schema={
                "datasource_id": {"type": "string", "required": False, "description": "Datasource ID"},
                "datasource_url": {"type": "string", "required": False, "description": "Connection string"},
                "datasource_type": {"type": "string", "required": False, "description": "postgres | mysql | sqlite"},
                "query": {"type": "string", "required": False, "description": "SQL query"},
                "limit": {"type": "integer", "required": False, "description": "Row limit"},
            },
            inputs={"query": Port(schema="string", required=False)},
            outputs={
                "preview_rows": Port(schema="list[dict]", required=False, description="Preview rows for UI and summaries."),
                "dataset_ref": Port(schema="dict", required=True, description="Reference to the materialized query result in sandbox storage."),
                "row_count": Port(schema="int", required=True, description="Materialized row count when available."),
                "columns": Port(schema="list[string]", required=False, description="Detected query result columns."),
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id, sandbox=None):
        return SqlExecuteHandler(db, user_id, sandbox=sandbox)
