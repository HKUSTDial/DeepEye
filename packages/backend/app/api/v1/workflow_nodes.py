"""Workflow node registry endpoints."""

from fastapi import APIRouter

from app.services.workflow_engine import build_registry

router = APIRouter(prefix="/workflow-nodes", tags=["workflow-nodes"])


@router.get("")
def list_workflow_nodes():
    registry = build_registry()
    return [spec.model_dump() for spec in registry.all()]
