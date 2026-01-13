from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class LimitRowsHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        limit = int(node.params.get("limit") or 100)
        return {"rows": rows[:limit]}


class LimitRowsNode(BaseNode):
    node_type = "data.limit_rows"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Limit the number of rows.",
            params_schema={
                "limit": {"type": "integer", "required": True, "description": "Max rows"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]", description="Limited rows.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return LimitRowsHandler()
