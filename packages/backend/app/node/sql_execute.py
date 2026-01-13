from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import DataSourceRepository
from app.node.base import BaseNode
from app.node.utils import create_engine, fetch_rows, validate_datasource_type
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class SqlExecuteHandler:
    def __init__(self, db: Session, user_id) -> None:
        self.db = db
        self.user_id = user_id

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
        rows = fetch_rows(engine, str(query), limit)
        return {"rows": rows}


class SqlExecuteNode(BaseNode):
    node_type = "sql.execute"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Execute SQL and return rows.",
            params_schema={
                "datasource_id": {"type": "string", "required": False, "description": "Datasource ID"},
                "datasource_url": {"type": "string", "required": False, "description": "Connection string"},
                "datasource_type": {"type": "string", "required": False, "description": "postgres | mysql | sqlite"},
                "query": {"type": "string", "required": False, "description": "SQL query"},
                "limit": {"type": "integer", "required": False, "description": "Row limit"},
            },
            inputs={"query": Port(schema="string", required=False)},
            outputs={"rows": Port(schema="list[dict]", description="Query result rows.")},
        )

    @classmethod
    def build_handler(cls, db: Session, user_id):
        return SqlExecuteHandler(db, user_id)
