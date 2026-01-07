"""Tests for workflow validation."""

from deepeye.workflows.examples import (
    build_accuracy_workflow,
    build_group_workflow,
    build_registry,
    build_simple_workflow,
)
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Port, Workflow
from deepeye.workflows.validation import validate_workflow_graph


def _schema_check(source_schema: object, target_schema: object) -> bool:
    if source_schema is None or target_schema is None:
        return True
    return source_schema == target_schema


def test_validate_simple_workflow_ok() -> None:
    registry = build_registry()
    workflow = build_simple_workflow()
    issues = validate_workflow_graph(workflow.root, registry=registry, schema_check=_schema_check)
    assert issues == []


def test_validate_group_workflow_ok() -> None:
    registry = build_registry()
    workflow = build_group_workflow()
    issues = validate_workflow_graph(workflow.root, registry=registry, schema_check=_schema_check)
    assert issues == []


def test_validate_accuracy_workflow_ok() -> None:
    registry = build_registry()
    workflow = build_accuracy_workflow()
    issues = validate_workflow_graph(workflow.root, registry=registry, schema_check=_schema_check)
    assert issues == []


def test_multiple_edge_violation_detected() -> None:
    node_a = Node(id="a", type="source", outputs={"out": Port(schema="string")})
    node_b = Node(
        id="b",
        type="transform",
        inputs={"in": Port(schema="string", required=True)},
        outputs={"out": Port(schema="string")},
    )
    node_c = Node(id="c", type="source", outputs={"out": Port(schema="string")})
    graph = Graph(
        nodes={"a": node_a, "b": node_b, "c": node_c},
        edges={
            "e1": Edge(
                id="e1",
                source=EdgeEndpoint(node_id="a", port_id="out"),
                target=EdgeEndpoint(node_id="b", port_id="in"),
            ),
            "e2": Edge(
                id="e2",
                source=EdgeEndpoint(node_id="c", port_id="out"),
                target=EdgeEndpoint(node_id="b", port_id="in"),
            ),
        },
    )
    workflow = Workflow(id="wf_invalid", root=graph)
    issues = validate_workflow_graph(workflow.root)
    assert any(issue.code == "input.multiple.violation" for issue in issues)
