from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class AggregateRowsHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        group_by_raw = node.params.get("group_by") or ""
        group_by = [c.strip() for c in str(group_by_raw).split(",") if c.strip()]
        agg_column = node.params.get("agg_column")
        agg_func = (node.params.get("agg_func") or "count").lower()
        output_field = node.params.get("output_field") or f"{agg_func}_{agg_column or 'rows'}"

        if not group_by:
            return {"rows": rows}

        groups: dict[tuple, list[dict]] = {}
        for row in rows:
            key = tuple(row.get(col) for col in group_by)
            groups.setdefault(key, []).append(row)

        aggregated: list[dict[str, Any]] = []
        for key, items in groups.items():
            values = [row.get(agg_column) for row in items] if agg_column else []
            numeric = [v for v in values if isinstance(v, (int, float))]
            if agg_func == "count":
                metric = len(items)
            elif agg_func == "sum":
                metric = sum(numeric)
            elif agg_func == "avg":
                metric = sum(numeric) / len(numeric) if numeric else 0
            elif agg_func == "min":
                metric = min(numeric) if numeric else None
            elif agg_func == "max":
                metric = max(numeric) if numeric else None
            else:
                metric = len(items)

            row_out = {col: key[idx] for idx, col in enumerate(group_by)}
            row_out[output_field] = metric
            aggregated.append(row_out)

        return {"rows": aggregated}


class AggregateRowsNode(BaseNode):
    node_type = "data.aggregate"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Group and aggregate rows.",
            params_schema={
                "group_by": {"type": "string", "required": True, "description": "Group-by columns"},
                "agg_column": {"type": "string", "required": False, "description": "Column to aggregate"},
                "agg_func": {
                    "type": "string",
                    "required": True,
                    "description": "count | sum | avg | min | max",
                },
                "output_field": {"type": "string", "required": False, "description": "Output column name"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]", description="Aggregated rows.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return AggregateRowsHandler()
