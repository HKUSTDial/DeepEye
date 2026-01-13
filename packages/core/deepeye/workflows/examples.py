"""Workflow examples and demo validation."""

from __future__ import annotations

from deepeye.workflows.engine import (
    ConditionHandler,
    ExecutionEngine,
    NodeHandler,
    TransformHandler,
)
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Port, Workflow
from deepeye.workflows.registry import NodeRegistry, NodeSpec
from deepeye.workflows.validation import validate_workflow_graph


def build_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register(
        NodeSpec(
            type="source",
            description="Provide initial text input.",
            outputs={"text": Port(schema="string")},
        )
    )
    registry.register(
        NodeSpec(
            type="transform",
            description="Transform input text to output text.",
            inputs={"text": Port(schema="string", required=True)},
            outputs={"text": Port(schema="string")},
        )
    )
    registry.register(
        NodeSpec(
            type="group",
            description="Group node with internal graph.",
        )
    )
    registry.register(
        NodeSpec(
            type="group_inputs",
            description="Group boundary inputs.",
        )
    )
    registry.register(
        NodeSpec(
            type="group_outputs",
            description="Group boundary outputs.",
        )
    )
    registry.register(
        NodeSpec(
            type="list_source",
            description="Provide a list input (labels or predictions).",
            outputs={"items": Port(schema="list[bool]")},
        )
    )
    registry.register(
        NodeSpec(
            type="compare",
            description="Compare predictions with labels.",
            inputs={
                "predictions": Port(schema="list[bool]", required=True),
                "labels": Port(schema="list[bool]", required=True),
            },
            outputs={"correct_flags": Port(schema="list[bool]")},
        )
    )
    registry.register(
        NodeSpec(
            type="accuracy",
            description="Compute accuracy from correctness flags.",
            inputs={"correct_flags": Port(schema="list[bool]", required=True)},
            outputs={"accuracy": Port(schema="float")},
        )
    )
    return registry


def build_simple_workflow() -> Workflow:
    nodes = {
        "n1": Node(
            id="n1",
            type="source",
            outputs={"text": Port(schema="string")},
            params={"text": "Hello"},
        ),
        "n2": Node(
            id="n2",
            type="transform",
            inputs={"text": Port(schema="string", required=True)},
            outputs={"text": Port(schema="string")},
        ),
    }
    edges = {
        "e1": Edge(
            id="e1",
            source=EdgeEndpoint(node_id="n1", port_id="text"),
            target=EdgeEndpoint(node_id="n2", port_id="text"),
            condition="non_empty",
            transform="lowercase",
        )
    }
    return Workflow(id="wf_simple", name="Simple workflow", root=Graph(nodes=nodes, edges=edges))


def build_group_workflow() -> Workflow:
    outer_source = Node(
        id="n_outer",
        type="source",
        outputs={"text": Port(schema="string")},
    )
    group_inputs = Node(
        id="gi1",
        type="group_inputs",
        outputs={"text": Port(schema="string")},
        params={"map": {"in_text": "text"}},
    )
    group_outputs = Node(
        id="go1",
        type="group_outputs",
        inputs={"text": Port(schema="string")},
        params={"map": {"text": "out_text"}},
    )
    inner_transform = Node(
        id="n_inner",
        type="transform",
        inputs={"text": Port(schema="string", required=True)},
        outputs={"text": Port(schema="string")},
    )
    inner_edges = {
        "ie1": Edge(
            id="ie1",
            source=EdgeEndpoint(node_id="gi1", port_id="text"),
            target=EdgeEndpoint(node_id="n_inner", port_id="text"),
        ),
        "ie2": Edge(
            id="ie2",
            source=EdgeEndpoint(node_id="n_inner", port_id="text"),
            target=EdgeEndpoint(node_id="go1", port_id="text"),
        ),
    }
    internal_graph = Graph(
        nodes={group_inputs.id: group_inputs, inner_transform.id: inner_transform, group_outputs.id: group_outputs},
        edges=inner_edges,
    )

    group_node = Node(
        id="g1",
        type="group",
        inputs={"in_text": Port(schema="string", required=True)},
        outputs={"out_text": Port(schema="string")},
        params={"graph": internal_graph},
    )
    outer_edges = {
        "oe1": Edge(
            id="oe1",
            source=EdgeEndpoint(node_id="n_outer", port_id="text"),
            target=EdgeEndpoint(node_id="g1", port_id="in_text"),
        )
    }
    outer_nodes = {"n_outer": outer_source, "g1": group_node}
    return Workflow(id="wf_group", name="Group workflow", root=Graph(nodes=outer_nodes, edges=outer_edges))


def build_accuracy_workflow() -> Workflow:
    nodes = {
        "labels": Node(
            id="labels",
            type="list_source",
            outputs={"items": Port(schema="list[bool]")},
            params={"items": [True, False, True, True, False]},
        ),
        "preds": Node(
            id="preds",
            type="list_source",
            outputs={"items": Port(schema="list[bool]")},
            params={"items": [True, True, True, False, False]},
        ),
        "compare": Node(
            id="compare",
            type="compare",
            inputs={
                "predictions": Port(schema="list[bool]", required=True),
                "labels": Port(schema="list[bool]", required=True),
            },
            outputs={"correct_flags": Port(schema="list[bool]")},
        ),
        "accuracy": Node(
            id="accuracy",
            type="accuracy",
            inputs={"correct_flags": Port(schema="list[bool]", required=True)},
            outputs={"accuracy": Port(schema="float")},
        ),
    }
    edges = {
        "e_labels": Edge(
            id="e_labels",
            source=EdgeEndpoint(node_id="labels", port_id="items"),
            target=EdgeEndpoint(node_id="compare", port_id="labels"),
        ),
        "e_preds": Edge(
            id="e_preds",
            source=EdgeEndpoint(node_id="preds", port_id="items"),
            target=EdgeEndpoint(node_id="compare", port_id="predictions"),
        ),
        "e_correct": Edge(
            id="e_correct",
            source=EdgeEndpoint(node_id="compare", port_id="correct_flags"),
            target=EdgeEndpoint(node_id="accuracy", port_id="correct_flags"),
        ),
    }
    return Workflow(
        id="wf_accuracy",
        name="Accuracy workflow",
        root=Graph(nodes=nodes, edges=edges),
    )


def _schema_check(source_schema: object, target_schema: object) -> bool:
    if source_schema is None or target_schema is None:
        return True
    return source_schema == target_schema


class ListSourceHandler(NodeHandler):
    def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
        return {"items": node.params.get("items", [])}


class TextSourceHandler(NodeHandler):
    def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
        return {"text": node.params.get("text", "")}


class UppercaseHandler(NodeHandler):
    def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
        text = str(inputs.get("text", ""))
        return {"text": text.upper()}


class CompareHandler(NodeHandler):
    def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
        preds = list(inputs.get("predictions", []))
        labels = list(inputs.get("labels", []))
        size = min(len(preds), len(labels))
        correct_flags = [preds[i] == labels[i] for i in range(size)]
        return {"correct_flags": correct_flags}


class AccuracyHandler(NodeHandler):
    def execute(self, node: Node, inputs: dict[str, object], context: object) -> dict[str, object]:
        flags = list(inputs.get("correct_flags", []))
        accuracy = (sum(1 for f in flags if f) / len(flags)) if flags else 0.0
        return {"accuracy": accuracy}


class NonEmptyCondition(ConditionHandler):
    def evaluate(self, value: object, context: object) -> bool:
        if value is None:
            return False
        if isinstance(value, list):
            return len(value) > 0
        return True


class LowercaseTransform(TransformHandler):
    def apply(self, value: object, context: object) -> object:
        return str(value).lower()


def _build_engine() -> ExecutionEngine:
    engine = ExecutionEngine(node_registry=build_registry(), schema_check=_schema_check)
    engine.register_handler("list_source", ListSourceHandler())
    engine.register_handler("source", TextSourceHandler())
    engine.register_handler("transform", UppercaseHandler())
    engine.register_handler("compare", CompareHandler())
    engine.register_handler("accuracy", AccuracyHandler())
    engine.register_condition("non_empty", NonEmptyCondition())
    engine.register_transform("lowercase", LowercaseTransform())
    return engine


def run_demo() -> None:
    registry = build_registry()
    engine = _build_engine()
    workflows = [build_simple_workflow(), build_group_workflow(), build_accuracy_workflow()]

    for workflow in workflows:
        issues = validate_workflow_graph(workflow.root, registry=registry, schema_check=_schema_check)
        if issues:
            print(f"[{workflow.id}] Issues:")
            for issue in issues:
                print(f" - {issue.code}: {issue.message} ({issue.location})")
        else:
            print(f"[{workflow.id}] OK")
            context = engine.run(workflow, validate=False)
            print(f"[{workflow.id}] Status: {context.status}")
            for node_id, run in context.runs.items():
                if run.outputs:
                    print(f" - {node_id}: {run.outputs}")


if __name__ == "__main__":
    run_demo()
