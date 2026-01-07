"""Workflow definition models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Position(BaseModel):
    """Canvas position in pixels."""

    x: float
    y: float


class Port(BaseModel):
    """Port contract definition."""

    schema_: str | dict[str, Any] | None = Field(default=None, alias="schema")
    required: bool = False
    multiple: bool = False
    default: Any | None = None
    examples: list[Any] | None = None
    description: str | None = None

    model_config = {"populate_by_name": True}


class EdgeEndpoint(BaseModel):
    """Edge endpoint reference."""

    node_id: str
    port_id: str


class Edge(BaseModel):
    """Connection between node ports."""

    id: str
    source: EdgeEndpoint
    target: EdgeEndpoint
    condition: str | None = None
    transform: str | None = None


class NodePolicy(BaseModel):
    """Execution policy hints."""

    timeout_seconds: int | None = None
    retry: int | None = None
    cache_key: str | None = None

    model_config = {"extra": "allow"}


class NodeMetadata(BaseModel):
    """UI metadata."""

    position: Position | None = None
    label: str | None = None
    tags: list[str] | None = None
    note: str | None = None

    model_config = {"extra": "allow"}


class Node(BaseModel):
    """Workflow node definition."""

    id: str
    type: str
    inputs: dict[str, Port] = Field(default_factory=dict)
    outputs: dict[str, Port] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    policy: NodePolicy | None = None
    metadata: NodeMetadata | None = None

    model_config = {"extra": "allow"}


class Graph(BaseModel):
    """Single-layer DAG."""

    nodes: dict[str, Node] = Field(default_factory=dict)
    edges: dict[str, Edge] = Field(default_factory=dict)


class Workflow(BaseModel):
    """Workflow container with a root graph."""

    id: str
    name: str | None = None
    description: str | None = None
    version: str | None = None
    root: Graph
