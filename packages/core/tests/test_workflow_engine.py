"""Tests for workflow execution engine."""

from deepeye.workflows.engine import ExecutionEngine
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Workflow
from deepeye.workflows.examples import (
    AccuracyHandler,
    CompareHandler,
    ListSourceHandler,
    LowercaseTransform,
    NonEmptyCondition,
    TextSourceHandler,
    UppercaseHandler,
    build_accuracy_workflow,
    build_registry,
    build_simple_workflow,
)


def test_engine_runs_accuracy_workflow() -> None:
    registry = build_registry()
    engine = ExecutionEngine(node_registry=registry)
    engine.register_handler("list_source", ListSourceHandler())
    engine.register_handler("compare", CompareHandler())
    engine.register_handler("accuracy", AccuracyHandler())

    workflow = build_accuracy_workflow()
    context = engine.run(workflow, validate=False)

    assert context.status == "success"
    assert context.runs["accuracy"].outputs["accuracy"] == 0.6


def test_engine_applies_condition_and_transform() -> None:
    registry = build_registry()
    engine = ExecutionEngine(node_registry=registry)
    engine.register_handler("source", TextSourceHandler())
    engine.register_handler("transform", UppercaseHandler())
    engine.register_condition("non_empty", NonEmptyCondition())
    engine.register_transform("lowercase", LowercaseTransform())

    workflow = build_simple_workflow()
    context = engine.run(workflow, validate=False)

    assert context.status == "success"
    assert context.runs["n2"].outputs["text"] == "HELLO"


def test_engine_uses_registry_ports_when_workflow_omits_port_contracts() -> None:
    registry = build_registry()
    engine = ExecutionEngine(node_registry=registry)
    engine.register_handler("source", TextSourceHandler())
    engine.register_handler("transform", UppercaseHandler())

    workflow = Workflow(
        id="wf_registry_ports",
        root=Graph(
            nodes={
                "n1": Node(id="n1", type="source", params={"text": "Hello"}),
                "n2": Node(id="n2", type="transform"),
            },
            edges={
                "e1": Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="n1", port_id="text"),
                    target=EdgeEndpoint(node_id="n2", port_id="text"),
                )
            },
        ),
    )

    context = engine.run(workflow)

    assert context.status == "success"
    assert context.runs["n2"].outputs["text"] == "HELLO"


def test_engine_rejects_undeclared_handler_outputs() -> None:
    class InvalidTransformHandler:
        def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
            del node, context
            return {"text": str(inputs.get("text", "")).upper(), "extra": "unexpected"}

    registry = build_registry()
    engine = ExecutionEngine(node_registry=registry)
    engine.register_handler("source", TextSourceHandler())
    engine.register_handler("transform", InvalidTransformHandler())

    workflow = Workflow(
        id="wf_invalid_outputs",
        root=Graph(
            nodes={
                "n1": Node(id="n1", type="source", params={"text": "Hello"}),
                "n2": Node(id="n2", type="transform"),
            },
            edges={
                "e1": Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="n1", port_id="text"),
                    target=EdgeEndpoint(node_id="n2", port_id="text"),
                )
            },
        ),
    )

    context = engine.run(workflow)

    assert context.status == "failed"
    assert context.runs["n2"].status == "failed"
    assert "undeclared outputs" in (context.runs["n2"].error or "")
