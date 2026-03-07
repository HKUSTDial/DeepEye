"""Node specification registry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from deepeye.workflows.models import Port


class NodeSpec(BaseModel):
    """Machine-readable node specification."""

    type: str
    description: str | None = None
    params_schema: dict[str, Any] | None = None
    inputs: dict[str, Port] = Field(default_factory=dict)
    outputs: dict[str, Port] = Field(default_factory=dict)
    version: str = "1.0"

    model_config = {"extra": "allow"}


class NodeRegistry:
    """Registry for node specs."""

    def __init__(self) -> None:
        self._specs: dict[str, NodeSpec] = {}

    def register(self, spec: NodeSpec) -> None:
        if spec.type in self._specs:
            raise ValueError(f"NodeSpec already registered: {spec.type}")
        self._specs[spec.type] = spec

    def get(self, node_type: str) -> NodeSpec | None:
        return self._specs.get(node_type)

    def require(self, node_type: str) -> NodeSpec:
        spec = self.get(node_type)
        if not spec:
            raise KeyError(f"NodeSpec not found: {node_type}")
        return spec

    def all(self) -> list[NodeSpec]:
        return list(self._specs.values())
