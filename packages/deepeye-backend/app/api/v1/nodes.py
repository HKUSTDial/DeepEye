"""Node API routes."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas.node import (
    NodeInfo,
    NodeListResponse,
    NodeExecutionRequest,
    NodeExecutionResult,
)
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["nodes"])

node_service = NodeService()


@router.get("", response_model=NodeListResponse)
async def list_nodes():
    """Get all registered nodes."""
    return node_service.get_all_nodes()


@router.get("/{node_type}", response_model=NodeInfo)
async def get_node_info(node_type: str):
    """Get detailed information about a node."""
    node_info = node_service.get_node_info(node_type)
    if not node_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node type '{node_type}' not found",
        )
    return node_info


@router.post("/{node_type}/execute", response_model=NodeExecutionResult)
async def execute_node(node_type: str, request: NodeExecutionRequest):
    """Execute a single node."""
    result = await node_service.execute_node(
        node_type=node_type,
        inputs=request.inputs,
        config=request.config,
    )
    
    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "Node execution failed",
        )
    
    return result

