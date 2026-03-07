"""Tests for builtin workflow transform and answer nodes."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from langchain_core.messages import AIMessage

from app.node.llm.answer import LLMAnswerHandler
from app.node.rows.basic import (
    RowsAggregateHandler,
    RowsFilterHandler,
    RowsProfileHandler,
    RowsSelectHandler,
    RowsSortHandler,
)
from deepeye.workflows.models import Node


class _FakeModel:
    def __init__(self) -> None:
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content="Grounded answer.")


def test_rows_select_filter_sort_and_profile_handlers() -> None:
    rows = [
        {"city": "Shanghai", "revenue": 120, "segment": "A"},
        {"city": "Beijing", "revenue": 80, "segment": "B"},
        {"city": "Shenzhen", "revenue": 150, "segment": "A"},
    ]

    selected = RowsSelectHandler().execute(
        Node(id="select", type="rows.select", params={"columns": ["city", "revenue"]}),
        {"rows": rows},
        context=None,
    )
    assert selected["rows"] == [
        {"city": "Shanghai", "revenue": 120},
        {"city": "Beijing", "revenue": 80},
        {"city": "Shenzhen", "revenue": 150},
    ]

    filtered = RowsFilterHandler().execute(
        Node(id="filter", type="rows.filter", params={"column": "segment", "operator": "eq", "value": "A"}),
        {"rows": rows},
        context=None,
    )
    assert [row["city"] for row in filtered["rows"]] == ["Shanghai", "Shenzhen"]

    sorted_rows = RowsSortHandler().execute(
        Node(id="sort", type="rows.sort", params={"column": "revenue", "descending": True}),
        {"rows": rows},
        context=None,
    )
    assert [row["city"] for row in sorted_rows["rows"]] == ["Shenzhen", "Shanghai", "Beijing"]

    profile = RowsProfileHandler().execute(
        Node(id="profile", type="rows.profile", params={"sample_size": 2}),
        {"rows": rows},
        context=None,
    )
    assert profile["row_count"] == 3
    assert profile["profile"]["column_count"] == 3
    revenue_profile = next(column for column in profile["profile"]["columns"] if column["name"] == "revenue")
    assert revenue_profile["numeric_summary"]["max"] == 150

    aggregated = RowsAggregateHandler().execute(
        Node(
            id="aggregate",
            type="rows.aggregate",
            params={
                "group_by": ["segment"],
                "metrics": [
                    {"column": "revenue", "op": "sum", "as": "total_revenue"},
                    {"column": "revenue", "op": "avg", "as": "avg_revenue"},
                    {"column": "city", "op": "count", "as": "row_count"},
                ],
            },
        ),
        {"rows": rows},
        context=None,
    )
    assert aggregated["rows"] == [
        {"segment": "A", "total_revenue": 270, "avg_revenue": 135.0, "row_count": 2},
        {"segment": "B", "total_revenue": 80, "avg_revenue": 80.0, "row_count": 1},
    ]


def test_llm_answer_handler_uses_grounded_payload() -> None:
    model = _FakeModel()
    handler = LLMAnswerHandler(model=model)

    result = handler.execute(
        Node(id="answer", type="llm.answer", params={"instructions": "Answer in Chinese."}),
        {
            "question": "哪个城市收入最高？",
            "rows": [{"city": "Shenzhen", "revenue": 150}],
            "context": [{"profile": {"row_count": 1}}],
            "artifacts": [{"kind": "report", "report_path": "/workspace/report.html"}],
        },
        context=None,
    )

    assert result["answer"] == "Grounded answer."
    assert model.messages is not None
    assert "哪个城市收入最高" in model.messages[1].content
    assert "Shenzhen" in model.messages[1].content
