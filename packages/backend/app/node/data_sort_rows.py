from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class SortRowsHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        column = node.params.get("column")
        order = (node.params.get("order") or "asc").lower()
        if not column:
            return {"rows": rows}
        reverse = order == "desc"

        def _sort_key(row: dict):
            value = row.get(column)
            return (value is None, value)

        return {"rows": sorted(rows, key=_sort_key, reverse=reverse)}


class SortRowsNode(BaseNode):
    node_type = "data.sort_rows"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Sort rows by a column.",
            params_schema={
                "column": {"type": "string", "required": True, "description": "Column name"},
                "order": {"type": "string", "required": True, "description": "asc | desc"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]", description="Sorted rows.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return SortRowsHandler()
