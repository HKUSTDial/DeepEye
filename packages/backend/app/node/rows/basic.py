from __future__ import annotations

from collections import Counter
from typing import Any

from app.node.core.base import BaseNode
from app.workflow.services.datasets import build_tabular_node_result, is_dataset_ref, read_dataset_ref_rows
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


def _require_dataset_ref(inputs: dict[str, Any], *, sandbox=None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dataset_ref = inputs.get("dataset_ref")
    if is_dataset_ref(dataset_ref):
        if sandbox is None:
            raise ValueError("dataset_ref input requires sandbox access")
        return read_dataset_ref_rows(dataset_ref, sandbox=sandbox, limit=None), dataset_ref

    raise ValueError("dataset_ref input is required")


def _parse_columns(value: Any) -> list[str]:
    if isinstance(value, list):
        columns = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        columns = [part.strip() for part in value.split(",") if part.strip()]
    else:
        raise ValueError("columns must be a list or comma-separated string")
    if not columns:
        raise ValueError("columns must not be empty")
    return columns


def _coerce_literal(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        try:
            if "." in lowered:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


def _match_filter(candidate: Any, operator: str, expected: Any, *, case_sensitive: bool) -> bool:
    if operator == "is_null":
        return candidate is None
    if operator == "not_null":
        return candidate is not None

    if operator in {"contains", "in", "not_in"}:
        if operator == "contains":
            if candidate is None:
                return False
            left = str(candidate)
            right = str(expected)
            if not case_sensitive:
                left = left.lower()
                right = right.lower()
            return right in left
        values = expected if isinstance(expected, list) else [expected]
        normalized_values = [str(item) if not case_sensitive else item for item in values]
        probe = str(candidate) if not case_sensitive else candidate
        if operator == "in":
            return probe in normalized_values
        return probe not in normalized_values

    left = _coerce_literal(candidate)
    right = _coerce_literal(expected)
    if isinstance(left, str) and isinstance(right, str) and not case_sensitive:
        left = left.lower()
        right = right.lower()

    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left is not None and right is not None and left > right
    if operator == "gte":
        return left is not None and right is not None and left >= right
    if operator == "lt":
        return left is not None and right is not None and left < right
    if operator == "lte":
        return left is not None and right is not None and left <= right
    raise ValueError(f"Unsupported operator: {operator}")


class _BaseRowsHandler:
    def __init__(self, sandbox=None) -> None:
        self.sandbox = sandbox

    def _table_result(
        self,
        rows: list[dict[str, Any]],
        *,
        input_dataset_ref: dict[str, Any],
        source: str,
        name_hint: str,
    ) -> dict[str, Any]:
        return build_tabular_node_result(
            rows,
            sandbox=self.sandbox,
            source=source,
            name_hint=name_hint,
        )


class RowsSelectHandler(_BaseRowsHandler):
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        rows, dataset_ref = _require_dataset_ref(inputs, sandbox=self.sandbox)
        columns = _parse_columns(node.params.get("columns"))
        selected = [{column: row.get(column) for column in columns} for row in rows]
        return self._table_result(
            selected,
            input_dataset_ref=dataset_ref,
            source="rows.select",
            name_hint=f"{node.id or 'rows_select'}_selected",
        )


class RowsFilterHandler(_BaseRowsHandler):
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        rows, dataset_ref = _require_dataset_ref(inputs, sandbox=self.sandbox)
        column = str(node.params.get("column") or "").strip()
        operator = str(node.params.get("operator") or "eq").strip()
        case_sensitive = bool(node.params.get("case_sensitive", False))
        if not column:
            raise ValueError("column is required")
        expected = node.params.get("value")
        filtered = [
            row
            for row in rows
            if _match_filter(row.get(column), operator, expected, case_sensitive=case_sensitive)
        ]
        return self._table_result(
            filtered,
            input_dataset_ref=dataset_ref,
            source="rows.filter",
            name_hint=f"{node.id or 'rows_filter'}_filtered",
        )


class RowsSortHandler(_BaseRowsHandler):
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        rows, dataset_ref = _require_dataset_ref(inputs, sandbox=self.sandbox)
        column = str(node.params.get("column") or "").strip()
        if not column:
            raise ValueError("column is required")
        descending = bool(node.params.get("descending", False))
        nulls_last = bool(node.params.get("nulls_last", True))

        def sort_key(row: dict[str, Any]) -> tuple[int, Any]:
            value = row.get(column)
            if value is None:
                return (1 if nulls_last else -1, "")
            return (0, value)

        return self._table_result(
            sorted(rows, key=sort_key, reverse=descending),
            input_dataset_ref=dataset_ref,
            source="rows.sort",
            name_hint=f"{node.id or 'rows_sort'}_sorted",
        )


class RowsProfileHandler(_BaseRowsHandler):
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        rows, dataset_ref = _require_dataset_ref(inputs, sandbox=self.sandbox)
        sample_size = int(node.params.get("sample_size") or 5)
        column_names = sorted({key for row in rows for key in row.keys()})
        columns: list[dict[str, Any]] = []

        for column in column_names:
            values = [row.get(column) for row in rows]
            non_null_values = [value for value in values if value is not None]
            type_counter = Counter(type(value).__name__ for value in non_null_values)
            top_type = type_counter.most_common(1)[0][0] if type_counter else "null"
            sample_values: list[Any] = []
            for value in non_null_values:
                if value not in sample_values:
                    sample_values.append(value)
                if len(sample_values) >= sample_size:
                    break

            column_profile: dict[str, Any] = {
                "name": column,
                "inferred_type": top_type,
                "null_count": len(values) - len(non_null_values),
                "non_null_count": len(non_null_values),
                "unique_count": len({repr(value) for value in non_null_values}),
                "sample_values": sample_values,
            }

            numeric_values = [value for value in non_null_values if isinstance(value, (int, float)) and not isinstance(value, bool)]
            if numeric_values:
                column_profile["numeric_summary"] = {
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "mean": sum(numeric_values) / len(numeric_values),
                }
            columns.append(column_profile)

        profile = {
            "row_count": len(rows),
            "column_count": len(column_names),
            "columns": columns,
        }
        result = self._table_result(
            rows,
            input_dataset_ref=dataset_ref,
            source="rows.profile",
            name_hint=f"{node.id or 'rows_profile'}_profiled",
        )
        result["profile"] = profile
        return result


class RowsAggregateHandler(_BaseRowsHandler):
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        rows, dataset_ref = _require_dataset_ref(inputs, sandbox=self.sandbox)
        group_by = node.params.get("group_by") or []
        metrics = node.params.get("metrics") or []
        group_columns = _parse_columns(group_by) if group_by else []
        if not isinstance(metrics, list) or not metrics:
            raise ValueError("metrics must be a non-empty list")

        grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for row in rows:
            key = tuple(row.get(column) for column in group_columns)
            grouped.setdefault(key, []).append(row)

        result_rows: list[dict[str, Any]] = []
        for key, bucket in grouped.items():
            output_row = {column: key[index] for index, column in enumerate(group_columns)}
            for metric in metrics:
                if not isinstance(metric, dict):
                    raise ValueError("each metric must be an object")
                column = str(metric.get("column") or "").strip()
                op = str(metric.get("op") or "").strip().lower()
                as_name = str(metric.get("as") or f"{column}_{op}").strip()
                values = [item.get(column) for item in bucket]
                numeric_values = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]

                if op == "count":
                    output_row[as_name] = len(bucket)
                elif op == "count_distinct":
                    output_row[as_name] = len({repr(value) for value in values if value is not None})
                elif op == "sum":
                    output_row[as_name] = sum(numeric_values)
                elif op == "avg":
                    output_row[as_name] = (sum(numeric_values) / len(numeric_values)) if numeric_values else None
                elif op == "min":
                    output_row[as_name] = min(numeric_values) if numeric_values else None
                elif op == "max":
                    output_row[as_name] = max(numeric_values) if numeric_values else None
                else:
                    raise ValueError(f"Unsupported aggregate op: {op}")
            result_rows.append(output_row)

        return self._table_result(
            result_rows,
            input_dataset_ref=dataset_ref,
            source="rows.aggregate",
            name_hint=f"{node.id or 'rows_aggregate'}_aggregated",
        )


class RowsSelectNode(BaseNode):
    node_type = "rows.select"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Select a subset of columns from a tabular dataset.",
            params_schema={
                "columns": {"type": "array[string]", "required": True, "description": "Columns to keep in the output dataset, in the same order."},
            },
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference for tabular input."),
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Resulting dataset after column selection."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        del db, user_id
        return RowsSelectHandler(sandbox=sandbox)


class RowsFilterNode(BaseNode):
    node_type = "rows.filter"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Filter rows by one column and one comparison operator.",
            params_schema={
                "column": {"type": "string", "required": True, "description": "Column to filter on."},
                "operator": {
                    "type": "string",
                    "required": True,
                    "description": "Comparison operator. Supported values: eq, ne, gt, gte, lt, lte, contains, in, not_in, is_null, not_null.",
                },
                "value": {"type": "any", "required": False, "description": "Comparison value when required by the operator."},
                "case_sensitive": {"type": "boolean", "required": False, "description": "Case-sensitive string matching."},
            },
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference for tabular input."),
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Filtered dataset."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        del db, user_id
        return RowsFilterHandler(sandbox=sandbox)


class RowsSortNode(BaseNode):
    node_type = "rows.sort"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Sort tabular rows by one column.",
            params_schema={
                "column": {"type": "string", "required": True, "description": "Column to sort by."},
                "descending": {"type": "boolean", "required": False, "description": "Sort in descending order."},
            },
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference for tabular input."),
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Sorted dataset."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        del db, user_id
        return RowsSortHandler(sandbox=sandbox)


class RowsProfileNode(BaseNode):
    node_type = "rows.profile"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Profile tabular rows and emit lightweight schema/statistics.",
            params_schema={},
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference for tabular input."),
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Original dataset reference passed through."),
                "profile": Port(schema="dict", required=True, description="Column-level schema and statistics summary."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        del db, user_id
        return RowsProfileHandler(sandbox=sandbox)


class RowsAggregateNode(BaseNode):
    node_type = "rows.aggregate"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Aggregate tabular rows by group columns and metric definitions.",
            params_schema={
                "group_by": {"type": "array[string]", "required": False, "description": "Columns used as grouping keys."},
                "metrics": {
                    "type": "array[object]",
                    "required": True,
                    "description": "Metric definitions. Each metric object uses {column, op, as}. Supported ops: count, count_distinct, sum, avg, min, max.",
                },
            },
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference for tabular input."),
            },
            outputs={
                "dataset_ref": Port(schema="dict", required=True, description="Aggregated dataset."),
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None):
        del db, user_id
        return RowsAggregateHandler(sandbox=sandbox)
