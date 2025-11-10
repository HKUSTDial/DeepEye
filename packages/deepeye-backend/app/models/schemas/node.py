"""Node Pydantic schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodePort(BaseModel):
    """Node port schema."""

    name: str = Field(..., description="Port name")
    label: Optional[str] = Field(None, description="Port label")
    schemas: List[Dict[str, Any]] = Field(default_factory=list, description="Port schemas")


class NodeMetadata(BaseModel):
    """Node metadata schema."""

    name: str = Field(..., description="Node type name")
    display_name: str = Field(default="", description="Display name")
    description: str = Field(default="", description="Node description")
    version: str = Field(default="0.1.0", description="Node version")
    author: str = Field(default="", description="Node author")


class NodeInfo(BaseModel):
    """Node information schema."""

    node_type: str = Field(..., description="Node type identifier")
    class_name: str = Field(..., description="Node class name")
    metadata: NodeMetadata = Field(..., description="Node metadata")
    input_ports: List[NodePort] = Field(default_factory=list, description="Input ports")
    output_ports: List[NodePort] = Field(default_factory=list, description="Output ports")


class NodeListItem(BaseModel):
    """Node list item schema (simplified)."""

    node_type: str = Field(..., description="Node type identifier")
    display_name: str = Field(..., description="Display name")
    description: str = Field(..., description="Node description")
    version: str = Field(..., description="Node version")


class NodeListResponse(BaseModel):
    """Node list response schema."""

    total: int = Field(..., description="Total number of nodes")
    nodes: List[NodeListItem] = Field(..., description="List of nodes")


class NodeExecutionRequest(BaseModel):
    """Node execution request schema."""

    inputs: Dict[str, Any] = Field(..., description="Node inputs")
    config: Optional[Dict[str, Any]] = Field(None, description="Node configuration")


class NodeExecutionResult(BaseModel):
    """Node execution result schema."""

    status: str = Field(..., description="Execution status (success/failed)")
    outputs: Dict[str, Any] = Field(..., description="Node outputs")
    execution_time: float = Field(..., description="Execution time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")

