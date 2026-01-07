from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class CorrelationHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        x_field = node.params.get("x_field")
        y_field = node.params.get("y_field")
        if not x_field or not y_field:
            raise ValueError("x_field and y_field are required")

        pairs = [
            (row.get(x_field), row.get(y_field))
            for row in rows
            if isinstance(row.get(x_field), (int, float)) and isinstance(row.get(y_field), (int, float))
        ]
        if len(pairs) < 2:
            return {"correlation": {"value": None, "count": len(pairs)}}

        xs, ys = zip(*pairs)
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
        den_x = sum((x - x_mean) ** 2 for x in xs)
        den_y = sum((y - y_mean) ** 2 for y in ys)
        denom = (den_x * den_y) ** 0.5
        value = num / denom if denom else None
        return {"correlation": {"value": value, "count": len(pairs)}}


class CorrelationNode(BaseNode):
    node_type = "stats.correlation"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Compute correlation between two numeric columns.",
            params_schema={
                "x_field": {"type": "string", "required": True, "description": "Numeric X column"},
                "y_field": {"type": "string", "required": True, "description": "Numeric Y column"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"correlation": Port(schema="dict", description="Correlation results.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return CorrelationHandler()
