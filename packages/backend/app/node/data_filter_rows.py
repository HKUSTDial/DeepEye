from __future__ import annotations

from typing import Any

from app.node.base import BaseNode
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class FilterRowsHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        rows = list(inputs.get("rows") or [])
        column = node.params.get("column")
        operator = node.params.get("operator") or "eq"
        value = node.params.get("value")
        if not column:
            return {"rows": rows}

        def _coerce(val: Any) -> Any:
            if isinstance(val, (int, float)):
                return val
            try:
                if isinstance(val, str) and "." in val:
                    return float(val)
                return int(val)
            except (ValueError, TypeError):
                return val

        target = _coerce(value)

        def _match(row: dict) -> bool:
            cell = _coerce(row.get(column))
            if operator == "eq":
                return cell == target
            if operator == "neq":
                return cell != target
            if operator == "gt":
                return isinstance(cell, (int, float)) and isinstance(target, (int, float)) and cell > target
            if operator == "gte":
                return isinstance(cell, (int, float)) and isinstance(target, (int, float)) and cell >= target
            if operator == "lt":
                return isinstance(cell, (int, float)) and isinstance(target, (int, float)) and cell < target
            if operator == "lte":
                return isinstance(cell, (int, float)) and isinstance(target, (int, float)) and cell <= target
            if operator == "contains":
                return target is not None and str(target) in str(cell)
            if operator == "in":
                if isinstance(target, (list, tuple, set)):
                    return cell in target
                return str(cell) in str(target or "")
            return False

        return {"rows": [row for row in rows if _match(row)]}


class FilterRowsNode(BaseNode):
    node_type = "data.filter_rows"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Filter rows by column condition.",
            params_schema={
                "column": {"type": "string", "required": True, "description": "Column name"},
                "operator": {
                    "type": "string",
                    "required": True,
                    "description": "eq | neq | gt | gte | lt | lte | contains | in",
                },
                "value": {"type": "string", "required": True, "description": "Target value"},
            },
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]", description="Filtered rows.")},
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return FilterRowsHandler()
