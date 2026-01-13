from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class SelectColumnsHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        columns_raw = node.params.get("columns") or ""
        columns = [c.strip() for c in str(columns_raw).split(",") if c.strip()]
        if not columns:
            return {"rows": rows}
        return {"rows": [{col: row.get(col) for col in columns} for row in rows]}


class SelectColumnsNode(BaseNode):
    node_type = "data.select_columns"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Select a subset of columns.",
            params_schema={
                "columns": {"type": "string", "required": True, "description": "Comma-separated column names"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]", description="Rows with selected columns.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return SelectColumnsHandler()
