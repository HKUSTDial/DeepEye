"""Workflow execution engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from deepeye.workflows.models import Graph, Node, Port, Workflow
from deepeye.workflows.registry import NodeRegistry, NodeSpec
from deepeye.workflows.runtime import ExecutionContext, NodeRun
from deepeye.workflows.validation import WorkflowValidationError, validate_workflow_graph

_DYNAMIC_PORT_NODE_TYPES = {"group", "group_inputs", "group_outputs"}


class NodeHandler(Protocol):
    """Execute a node with resolved inputs."""

    def execute(self, node: Node, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]: ...


class ConditionHandler(Protocol):
    """Decide whether an edge should pass values."""

    def evaluate(self, value: Any, context: ExecutionContext) -> bool: ...


class TransformHandler(Protocol):
    """Transform values on an edge."""

    def apply(self, value: Any, context: ExecutionContext) -> Any: ...


class HandlerRegistry:
    """Registry of runtime handlers keyed by node type."""

    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {}

    def register(self, node_type: str, handler: NodeHandler) -> None:
        if node_type in self._handlers:
            raise ValueError(f"Handler already registered: {node_type}")
        self._handlers[node_type] = handler

    def get(self, node_type: str) -> NodeHandler | None:
        return self._handlers.get(node_type)

    def require(self, node_type: str) -> NodeHandler:
        handler = self.get(node_type)
        if not handler:
            raise KeyError(f"Handler not found: {node_type}")
        return handler


class ConditionRegistry:
    """Registry of edge conditions keyed by name."""

    def __init__(self) -> None:
        self._handlers: dict[str, ConditionHandler] = {}

    def register(self, name: str, handler: ConditionHandler) -> None:
        if name in self._handlers:
            raise ValueError(f"Condition already registered: {name}")
        self._handlers[name] = handler

    def get(self, name: str) -> ConditionHandler | None:
        return self._handlers.get(name)

    def require(self, name: str) -> ConditionHandler:
        handler = self.get(name)
        if not handler:
            raise KeyError(f"Condition not found: {name}")
        return handler


class TransformRegistry:
    """Registry of edge transforms keyed by name."""

    def __init__(self) -> None:
        self._handlers: dict[str, TransformHandler] = {}

    def register(self, name: str, handler: TransformHandler) -> None:
        if name in self._handlers:
            raise ValueError(f"Transform already registered: {name}")
        self._handlers[name] = handler

    def get(self, name: str) -> TransformHandler | None:
        return self._handlers.get(name)

    def require(self, name: str) -> TransformHandler:
        handler = self.get(name)
        if not handler:
            raise KeyError(f"Transform not found: {name}")
        return handler


class ExecutionEngine:
    """Execute a workflow using registered node handlers."""

    def __init__(
        self,
        *,
        node_registry: NodeRegistry | None = None,
        handler_registry: HandlerRegistry | None = None,
        condition_registry: ConditionRegistry | None = None,
        transform_registry: TransformRegistry | None = None,
        schema_check: callable | None = None,
    ) -> None:
        self.node_registry = node_registry
        self.handlers = handler_registry or HandlerRegistry()
        self.conditions = condition_registry or ConditionRegistry()
        self.transforms = transform_registry or TransformRegistry()
        self.schema_check = schema_check

    def register_handler(self, node_type: str, handler: NodeHandler) -> None:
        self.handlers.register(node_type, handler)

    def register_condition(self, name: str, handler: ConditionHandler) -> None:
        self.conditions.register(name, handler)

    def register_transform(self, name: str, handler: TransformHandler) -> None:
        self.transforms.register(name, handler)

    def run(
        self,
        workflow: Workflow,
        *,
        validate: bool = True,
        on_node_start: callable | None = None,
        on_node_end: callable | None = None,
    ) -> ExecutionContext:
        if validate:
            issues = validate_workflow_graph(
                workflow.root,
                registry=self.node_registry,
                schema_check=self.schema_check,
            )
            if issues:
                raise WorkflowValidationError(issues)

        context = ExecutionContext(
            workflow_id=workflow.id,
            runs={node_id: NodeRun(node_id=node_id) for node_id in workflow.root.nodes},
            status="running",
            started_at=_utc_now(),
        )

        order = _topological_sort(workflow.root)
        for node_id in order:
            node = workflow.root.nodes[node_id]
            run = context.runs[node_id]
            run.status = "running"
            run.started_at = _utc_now()
            if on_node_start:
                on_node_start(node_id, run, context)

            try:
                inputs = _resolve_inputs(
                    workflow.root,
                    node,
                    context,
                    self.conditions,
                    self.transforms,
                    self.node_registry,
                )
                run.inputs = inputs
                handler = self.handlers.require(node.type)
                outputs = _validate_handler_outputs(
                    node,
                    handler.execute(node, inputs, context),
                    self.node_registry.get(node.type) if self.node_registry else None,
                )
                run.outputs = outputs
                run.status = "success"
            except Exception as exc:  # noqa: BLE001 - surface error for runtime
                run.status = "failed"
                run.error = str(exc)
                context.status = "failed"
                run.finished_at = _utc_now()
                if on_node_end:
                    on_node_end(node_id, run, context)
                context.finished_at = _utc_now()
                return context

            run.finished_at = _utc_now()
            if on_node_end:
                on_node_end(node_id, run, context)

        context.status = "success"
        context.finished_at = _utc_now()
        return context


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _topological_sort(graph: Graph) -> list[str]:
    indegree: dict[str, int] = {node_id: 0 for node_id in graph.nodes}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges.values():
        adjacency.setdefault(edge.source.node_id, []).append(edge.target.node_id)
        indegree[edge.target.node_id] = indegree.get(edge.target.node_id, 0) + 1

    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    order: list[str] = []
    while queue:
        node_id = queue.pop(0)
        order.append(node_id)
        for neighbor in adjacency.get(node_id, []):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    return order


def _resolve_inputs(
    graph: Graph,
    node: Node,
    context: ExecutionContext,
    conditions: ConditionRegistry,
    transforms: TransformRegistry,
    registry: NodeRegistry | None,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    resolved_inputs = _node_inputs(node, registry)
    incoming = [edge for edge in graph.edges.values() if edge.target.node_id == node.id]

    for edge in incoming:
        source_run = context.runs.get(edge.source.node_id)
        if not source_run:
            continue
        value = source_run.outputs.get(edge.source.port_id)
        if edge.condition:
            cond = conditions.require(edge.condition)
            if not cond.evaluate(value, context):
                continue
        if edge.transform:
            transform = transforms.require(edge.transform)
            value = transform.apply(value, context)
        target_port = resolved_inputs.get(edge.target.port_id) or node.inputs.get(edge.target.port_id)
        if target_port and target_port.multiple:
            inputs.setdefault(edge.target.port_id, [])
            if value is not None:
                inputs[edge.target.port_id].append(value)
        else:
            if value is not None:
                inputs[edge.target.port_id] = value

    for port_id, port in resolved_inputs.items():
        if port_id not in inputs:
            default = _default_for_port(port)
            if default is not None:
                inputs[port_id] = default
            elif port.required:
                raise ValueError(f"Required input missing: {node.id}.{port_id}")

    return inputs


def _node_inputs(
    node: Node,
    registry: NodeRegistry | None,
) -> dict[str, Port]:
    if registry:
        spec = registry.get(node.type)
        if spec:
            if node.type in _DYNAMIC_PORT_NODE_TYPES:
                return node.inputs
            return spec.inputs
    return node.inputs


def _validate_handler_outputs(
    node: Node,
    outputs: dict[str, Any] | None,
    spec: NodeSpec | None,
) -> dict[str, Any]:
    if outputs is None:
        outputs = {}
    if not isinstance(outputs, dict):
        raise TypeError(f"Node handler must return a dict: {node.type}")
    if not spec:
        return outputs

    unexpected_keys = sorted(set(outputs) - set(spec.outputs))
    if unexpected_keys:
        raise ValueError(
            f"Node {node.id} returned undeclared outputs for {node.type}: {', '.join(unexpected_keys)}"
        )

    missing_required = sorted(
        port_id
        for port_id, port in spec.outputs.items()
        if port.required and port_id not in outputs
    )
    if missing_required:
        raise ValueError(
            f"Node {node.id} did not return required outputs for {node.type}: {', '.join(missing_required)}"
        )
    return outputs


def _default_for_port(port: Port) -> Any | None:
    if port.default is None:
        return None
    if port.multiple and not isinstance(port.default, list):
        return [port.default]
    return port.default
