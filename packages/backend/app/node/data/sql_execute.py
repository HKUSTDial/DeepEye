from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.datasource.services.specs import validate_database_datasource_type
from app.infra.db import create_engine, fetch_rows
from app.repositories import DataSourceRepository
from app.node.core.base import BaseNode
from app.workflow.services.datasets import build_dataset_ref, materialize_sql_query_to_sandbox_result
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class SqlExecuteHandler:
    def __init__(self, db: Session, user_id, sandbox=None) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del inputs, context
        datasource_id = node.params.get("datasource_id")
        query = node.params.get("query")
        limit = int(node.params.get("limit") or 500)
        if not query:
            raise ValueError("query is required")
        if not datasource_id:
            raise ValueError("datasource_id is required")

        ds = DataSourceRepository(self.db).get_by_id_and_user(datasource_id, self.user_id)
        if not ds:
            raise ValueError("datasource not found")
        if getattr(ds, "category", "database") != "database":
            raise ValueError("sql.execute only supports database datasources")

        connection_string = ds.connection_string
        datasource_type = getattr(ds, "type", None)
        validate_database_datasource_type(datasource_type)
        if not connection_string:
            raise ValueError("database datasource is missing connection_string")

        engine = create_engine(connection_string)
        if self.sandbox:
            result = materialize_sql_query_to_sandbox_result(
                db=self.db,
                user_id=self.user_id,
                sandbox=self.sandbox,
                datasource_id=datasource_id,
                datasource_url=connection_string,
                datasource_type=datasource_type,
                query=str(query),
                name_hint=f"{node.id}_query",
                source="sql.execute",
                preview_limit=limit,
            )
            return {"dataset_ref": result["dataset_ref"]}

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
        return {"dataset_ref": dataset_ref}


class SqlExecuteNode(BaseNode):
    node_type = "sql.execute"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Execute SQL against one attached database datasource, materialize the result, and return a dataset_ref. The downstream schema is exactly the SQL SELECT list and aliases.",
            params_schema={
                "datasource_id": {"type": "string", "required": True, "description": "Attached database datasource id to query."},
                "query": {"type": "string", "required": True, "description": "SQL query to execute. Prefer returning only the rows needed downstream. Use explicit AS aliases for derived, aggregated, renamed, or ambiguous columns so downstream nodes receive stable column names."},
                "limit": {"type": "integer", "required": False, "description": "Preview row limit stored inside the returned `dataset_ref`. Defaults to 500."},
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Reference to the full materialized query result. Preview rows and detected columns live inside this object."),
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id, sandbox=None):
        return SqlExecuteHandler(db, user_id, sandbox=sandbox)
