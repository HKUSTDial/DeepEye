from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class StatsSummaryHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        if not rows:
            return {"summary": {"count": 0, "columns": []}}

        columns = list(rows[0].keys())
        summary: dict[str, Any] = {"count": len(rows), "columns": columns, "numeric": {}}

        for col in columns:
            values = [row.get(col) for row in rows if isinstance(row.get(col), (int, float))]
            if not values:
                continue
            summary["numeric"][col] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }
        return {"summary": summary}


class StatsSummaryNode(BaseNode):
    node_type = "stats.summary"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Compute summary statistics.",
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"summary": Port(schema="dict", description="Summary statistics for input rows.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return StatsSummaryHandler()
