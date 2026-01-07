"""Tests for workflow execution engine."""

from deepeye.workflows.engine import ExecutionEngine
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
