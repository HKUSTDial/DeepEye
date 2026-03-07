"""Tests for builtin workflow transform and answer nodes."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from langchain_core.messages import AIMessage

from app.services.workflow_engine import build_engine
from app.node.llm.answer import LLMAnswerHandler
from app.node.rows.basic import (
    RowsAggregateHandler,
    RowsFilterHandler,
    RowsProfileHandler,
    RowsSelectHandler,
    RowsSortHandler,
)
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Port, Workflow
from deepeye.workflows.registry import NodeSpec


class _FakeModel:
    def __init__(self) -> None:
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(content="Grounded answer.")


class _RowsSourceHandler:
    def execute(self, node: Node, inputs, context):
        del node, inputs, context
        return {
            "rows": [
                {"segment": "A", "revenue": 120},
                {"segment": "A", "revenue": 150},
                {"segment": "B", "revenue": 80},
            ]
        }


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


def test_workflow_engine_runs_rows_pipeline_with_llm_answer() -> None:
    model = _FakeModel()
    engine = build_engine(db=None, user_id=None, model=model)
    engine.node_registry.register(
        NodeSpec(
            type="rows.source",
            outputs={"rows": Port(schema="list[dict]", required=True)},
        )
    )
    engine.register_handler("rows.source", _RowsSourceHandler())

    workflow = Workflow(
        id="wf_rows_answer",
        root=Graph(
            nodes={
                "source": Node(id="source", type="rows.source"),
                "filter": Node(
                    id="filter",
                    type="rows.filter",
                    params={"column": "segment", "operator": "eq", "value": "A"},
                ),
                "aggregate": Node(
                    id="aggregate",
                    type="rows.aggregate",
                    params={"metrics": [{"column": "revenue", "op": "sum", "as": "total_revenue"}]},
                ),
                "answer": Node(
                    id="answer",
                    type="llm.answer",
                    params={"question": "A 分组的总收入是多少？"},
                ),
            },
            edges={
                "e1": Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="source", port_id="rows"),
                    target=EdgeEndpoint(node_id="filter", port_id="rows"),
                ),
                "e2": Edge(
                    id="e2",
                    source=EdgeEndpoint(node_id="filter", port_id="rows"),
                    target=EdgeEndpoint(node_id="aggregate", port_id="rows"),
                ),
                "e3": Edge(
                    id="e3",
                    source=EdgeEndpoint(node_id="aggregate", port_id="rows"),
                    target=EdgeEndpoint(node_id="answer", port_id="rows"),
                ),
            },
        ),
    )

    context = engine.run(workflow)

    assert context.status == "success"
    assert context.runs["aggregate"].outputs["rows"] == [{"total_revenue": 270}]
    assert context.runs["answer"].outputs["answer"] == "Grounded answer."
