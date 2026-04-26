"""Workflow validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from deepeye.workflows.models import Graph, Node, Port
from deepeye.workflows.registry import NodeRegistry, NodeSpec


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    location: str | None = None


class WorkflowValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        super().__init__("Workflow validation failed")
        self.issues = issues


SchemaCheck = Callable[[Any, Any], bool]
_DYNAMIC_PORT_NODE_TYPES = {"group", "group_inputs", "group_outputs"}


def _port_schema(port: Port | None) -> Any:
    return getattr(port, "schema_", None) if port else None


def _field_was_explicitly_set(port: Port, *field_names: str) -> bool:
    fields_set = getattr(port, "model_fields_set", set())
    return any(field_name in fields_set for field_name in field_names)


def _spec_for_node(node: Node, registry: NodeRegistry | None) -> NodeSpec | None:
    return registry.get(node.type) if registry else None


def _node_inputs(node: Node, registry: NodeRegistry | None) -> dict[str, Port]:
    spec = _spec_for_node(node, registry)
    if spec and node.type in _DYNAMIC_PORT_NODE_TYPES:
        return node.inputs
    return spec.inputs if spec else node.inputs


def _node_outputs(node: Node, registry: NodeRegistry | None) -> dict[str, Port]:
    spec = _spec_for_node(node, registry)
    if spec and node.type in _DYNAMIC_PORT_NODE_TYPES:
        return node.outputs
    return spec.outputs if spec else node.outputs


def validate_workflow_graph(
    graph: Graph,
    *,
    registry: NodeRegistry | None = None,
    schema_check: SchemaCheck | None = None,
    location_prefix: str = "",
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def _loc(path: str) -> str:
        return f"{location_prefix}{path}" if location_prefix else path

    issues.extend(_validate_nodes(graph, registry, _loc))
    issues.extend(_validate_required_params(graph, registry, _loc))
    issues.extend(_validate_edges(graph, registry, schema_check, _loc))
    issues.extend(_validate_required_inputs(graph, registry, _loc))
    issues.extend(_validate_group_nodes(graph, registry, schema_check, _loc))
    issues.extend(_validate_dag(graph, _loc))

    return issues


def _validate_required_params(
    graph: Graph,
    registry: NodeRegistry | None,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not registry:
        return issues

    for node in graph.nodes.values():
        spec = registry.get(node.type)
        if not spec or not spec.params_schema:
            continue
        for param_id, meta in spec.params_schema.items():
            if not isinstance(meta, dict) or not meta.get("required"):
                continue
            value = node.params.get(param_id)
            if value in (None, "", [], {}):
                issues.append(
                    ValidationIssue(
                        code="param.required.missing",
                        message=f"Required param missing: {node.id}.{param_id}",
                        location=loc(f"nodes.{node.id}.params.{param_id}"),
                    )
                )
    return issues


def _validate_nodes(
    graph: Graph,
    registry: NodeRegistry | None,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not registry:
        return issues

    for node in graph.nodes.values():
        spec = registry.get(node.type)
        if not spec:
            issues.append(
                ValidationIssue(
                    code="node.type.unknown",
                    message=f"Node type not registered: {node.type}",
                    location=loc(f"nodes.{node.id}.type"),
                )
            )
            continue

        issues.extend(_validate_declared_ports_against_spec(node, spec, loc))
    return issues


def _validate_declared_ports_against_spec(
    node: Node,
    spec: NodeSpec,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if node.type in _DYNAMIC_PORT_NODE_TYPES:
        return issues
    issues.extend(_validate_port_set(node, spec, "inputs", loc))
    issues.extend(_validate_port_set(node, spec, "outputs", loc))
    return issues


def _validate_port_set(
    node: Node,
    spec: NodeSpec,
    field_name: str,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    declared_ports = getattr(node, field_name)
    spec_ports = getattr(spec, field_name)
    port_kind = field_name[:-1]

    for port_id, port in declared_ports.items():
        spec_port = spec_ports.get(port_id)
        if not spec_port:
            issues.append(
                ValidationIssue(
                    code=f"node.{port_kind}.unknown",
                    message=f"{port_kind.capitalize()} port not defined by spec: {node.id}.{port_id}",
                    location=loc(f"nodes.{node.id}.{field_name}.{port_id}"),
                )
            )
            continue

        if _field_was_explicitly_set(port, "schema", "schema_") and _port_schema(port) != _port_schema(spec_port):
            issues.append(
                ValidationIssue(
                    code=f"node.{port_kind}.schema.mismatch",
                    message=f"{port_kind.capitalize()} schema mismatch for {node.id}.{port_id}",
                    location=loc(f"nodes.{node.id}.{field_name}.{port_id}.schema"),
                )
            )
        if _field_was_explicitly_set(port, "required") and port.required != spec_port.required:
            issues.append(
                ValidationIssue(
                    code=f"node.{port_kind}.required.mismatch",
                    message=f"{port_kind.capitalize()} required flag mismatch for {node.id}.{port_id}",
                    location=loc(f"nodes.{node.id}.{field_name}.{port_id}.required"),
                )
            )
        if _field_was_explicitly_set(port, "multiple") and port.multiple != spec_port.multiple:
            issues.append(
                ValidationIssue(
                    code=f"node.{port_kind}.multiple.mismatch",
                    message=f"{port_kind.capitalize()} multiplicity mismatch for {node.id}.{port_id}",
                    location=loc(f"nodes.{node.id}.{field_name}.{port_id}.multiple"),
                )
            )

    return issues


def _validate_edges(
    graph: Graph,
    registry: NodeRegistry | None,
    schema_check: SchemaCheck | None,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for edge in graph.edges.values():
        source_node = graph.nodes.get(edge.source.node_id)
        target_node = graph.nodes.get(edge.target.node_id)
        if not source_node:
            issues.append(
                ValidationIssue(
                    code="edge.source.missing",
                    message=f"Source node missing: {edge.source.node_id}",
                    location=loc(f"edges.{edge.id}.source"),
                )
            )
            continue
        if not target_node:
            issues.append(
                ValidationIssue(
                    code="edge.target.missing",
                    message=f"Target node missing: {edge.target.node_id}",
                    location=loc(f"edges.{edge.id}.target"),
                )
            )
            continue
        source_ports = _node_outputs(source_node, registry)
        target_ports = _node_inputs(target_node, registry)
        if edge.source.port_id not in source_ports:
            issues.append(
                ValidationIssue(
                    code="edge.source.port.missing",
                    message=f"Source port missing: {edge.source.port_id}",
                    location=loc(f"edges.{edge.id}.source.port_id"),
                )
            )
        if edge.target.port_id not in target_ports:
            issues.append(
                ValidationIssue(
                    code="edge.target.port.missing",
                    message=f"Target port missing: {edge.target.port_id}",
                    location=loc(f"edges.{edge.id}.target.port_id"),
                )
            )
        if schema_check and edge.target.port_id in target_ports:
            src_port = source_ports.get(edge.source.port_id)
            tgt_port = target_ports.get(edge.target.port_id)
            if src_port and tgt_port and not schema_check(_port_schema(src_port), _port_schema(tgt_port)):
                issues.append(
                    ValidationIssue(
                        code="edge.schema.incompatible",
                        message=(
                            f"Incompatible schema from {edge.source.node_id}.{edge.source.port_id} "
                            f"to {edge.target.node_id}.{edge.target.port_id}"
                        ),
                        location=loc(f"edges.{edge.id}"),
                    )
                )
    return issues


def _validate_required_inputs(
    graph: Graph,
    registry: NodeRegistry | None,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    incoming: dict[tuple[str, str], int] = {}
    for edge in graph.edges.values():
        key = (edge.target.node_id, edge.target.port_id)
        incoming[key] = incoming.get(key, 0) + 1

    for node in graph.nodes.values():
        spec = registry.get(node.type) if registry else None
        inputs = spec.inputs if spec else node.inputs
        for port_id, port in inputs.items():
            count = incoming.get((node.id, port_id), 0)
            if not port.multiple and count > 1:
                issues.append(
                    ValidationIssue(
                        code="input.multiple.violation",
                        message=f"Input {node.id}.{port_id} does not allow multiple edges",
                        location=loc(f"nodes.{node.id}.inputs.{port_id}"),
                    )
                )
            if port.required and count == 0 and port.default is None:
                issues.append(
                    ValidationIssue(
                        code="input.required.missing",
                        message=f"Required input missing: {node.id}.{port_id}",
                        location=loc(f"nodes.{node.id}.inputs.{port_id}"),
                    )
                )
    return issues


def _validate_group_nodes(
    graph: Graph,
    registry: NodeRegistry | None,
    schema_check: SchemaCheck | None,
    loc: Callable[[str], str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for node in graph.nodes.values():
        if node.type != "group":
            continue

        internal_graph = node.params.get("graph")
        if not isinstance(internal_graph, Graph):
            issues.append(
                ValidationIssue(
                    code="group.graph.missing",
                    message=f"Group node missing internal graph: {node.id}",
                    location=loc(f"nodes.{node.id}.params.graph"),
                )
            )
            continue

        issues.extend(
            validate_workflow_graph(
                internal_graph,
                registry=registry,
                schema_check=schema_check,
                location_prefix=loc(f"nodes.{node.id}.params.graph."),
            )
        )

        issues.extend(_validate_group_mappings(node, internal_graph, loc))
    return issues


def _validate_group_mappings(node: Node, internal_graph: Graph, loc: Callable[[str], str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    external_inputs = set(node.inputs.keys())
    external_outputs = set(node.outputs.keys())

    mapped_inputs: set[str] = set()
    mapped_outputs: set[str] = set()

    for internal_node in internal_graph.nodes.values():
        if internal_node.type == "group_inputs":
            mapping = internal_node.params.get("map", {})
            if not isinstance(mapping, dict):
                issues.append(
                    ValidationIssue(
                        code="group.inputs.map.invalid",
                        message=f"group_inputs map must be a dict in {internal_node.id}",
                        location=loc(f"nodes.{node.id}.params.graph.nodes.{internal_node.id}.params.map"),
                    )
                )
                continue
            for external_in, internal_out in mapping.items():
                if external_in not in external_inputs:
                    issues.append(
                        ValidationIssue(
                            code="group.inputs.external.missing",
                            message=f"External input missing: {external_in}",
                            location=loc(f"nodes.{node.id}.inputs.{external_in}"),
                        )
                    )
                if internal_out not in internal_node.outputs:
                    issues.append(
                        ValidationIssue(
                            code="group.inputs.internal.missing",
                            message=f"Internal output missing: {internal_out}",
                            location=loc(f"nodes.{node.id}.params.graph.nodes.{internal_node.id}.outputs.{internal_out}"),
                        )
                    )
                mapped_inputs.add(external_in)

        if internal_node.type == "group_outputs":
            mapping = internal_node.params.get("map", {})
            if not isinstance(mapping, dict):
                issues.append(
                    ValidationIssue(
                        code="group.outputs.map.invalid",
                        message=f"group_outputs map must be a dict in {internal_node.id}",
                        location=loc(f"nodes.{node.id}.params.graph.nodes.{internal_node.id}.params.map"),
                    )
                )
                continue
            for internal_in, external_out in mapping.items():
                if internal_in not in internal_node.inputs:
                    issues.append(
                        ValidationIssue(
                            code="group.outputs.internal.missing",
                            message=f"Internal input missing: {internal_in}",
                            location=loc(f"nodes.{node.id}.params.graph.nodes.{internal_node.id}.inputs.{internal_in}"),
                        )
                    )
                if external_out not in external_outputs:
                    issues.append(
                        ValidationIssue(
                            code="group.outputs.external.missing",
                            message=f"External output missing: {external_out}",
                            location=loc(f"nodes.{node.id}.outputs.{external_out}"),
                        )
                    )
                mapped_outputs.add(external_out)

    missing_inputs = external_inputs - mapped_inputs
    for port_id in missing_inputs:
        issues.append(
            ValidationIssue(
                code="group.inputs.unmapped",
                message=f"External input not mapped: {port_id}",
                location=loc(f"nodes.{node.id}.inputs.{port_id}"),
            )
        )

    missing_outputs = external_outputs - mapped_outputs
    for port_id in missing_outputs:
        issues.append(
            ValidationIssue(
                code="group.outputs.unmapped",
                message=f"External output not mapped: {port_id}",
                location=loc(f"nodes.{node.id}.outputs.{port_id}"),
            )
        )

    return issues


def _validate_dag(graph: Graph, loc: Callable[[str], str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in graph.nodes}
    for edge in graph.edges.values():
        adjacency.setdefault(edge.source.node_id, set()).add(edge.target.node_id)

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return False
        if node_id in visited:
            return True
        visiting.add(node_id)
        for neighbor in adjacency.get(node_id, set()):
            if not visit(neighbor):
                return False
        visiting.remove(node_id)
        visited.add(node_id)
        return True

    for node_id in adjacency:
        if node_id not in visited:
            if not visit(node_id):
                issues.append(
                    ValidationIssue(
                        code="graph.cycle",
                        message="Graph contains a cycle",
                        location=loc("edges"),
                    )
                )
                break
    return issues
