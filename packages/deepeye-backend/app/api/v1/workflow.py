"""Workflow API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, status, Query

from app.dependencies import CurrentUserDep, DatabaseDep
from app.models.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListItem,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])

workflow_service = WorkflowService()


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Create a new workflow."""
    workflow = await workflow_service.create_workflow(
        db=db,
        user_id=current_user.id,
        workflow_data=workflow_data,
    )
    return workflow


@router.get("", response_model=List[WorkflowListItem])
async def list_workflows(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    skip: int = Query(0, ge=0, description="Number of workflows to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of workflows to return"),
):
    """List all workflows for the current user."""
    workflows = await workflow_service.get_user_workflows(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Get a workflow by ID."""
    workflow = await workflow_service.get_workflow_by_id(
        db=db,
        workflow_id=workflow_id,
        user_id=current_user.id,
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Update a workflow."""
    workflow = await workflow_service.update_workflow(
        db=db,
        workflow_id=workflow_id,
        user_id=current_user.id,
        workflow_data=workflow_data,
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Delete a workflow."""
    success = await workflow_service.delete_workflow(
        db=db,
        workflow_id=workflow_id,
        user_id=current_user.id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

