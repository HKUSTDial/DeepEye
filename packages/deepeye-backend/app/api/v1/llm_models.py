"""LLM model management API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.dependencies import CurrentUserDep, DatabaseDep
from app.models.schemas.llm import LLMModel, LLMModelCreate, LLMModelUpdate
from app.services.llm_service import LLMService

router = APIRouter(prefix="/llm-models", tags=["llm-models"])

llm_service = LLMService()


@router.post("", response_model=LLMModel, status_code=status.HTTP_201_CREATED)
async def create_llm_model(
    llm_data: LLMModelCreate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Register a new LLM model for the authenticated user."""
    llm_model = await llm_service.create_llm_model(
        db=db,
        user_id=current_user.id,
        llm_data=llm_data,
    )
    return llm_model


@router.get("", response_model=List[LLMModel])
async def list_llm_models(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    skip: int = Query(0, ge=0, description="Number of models to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of models to return"),
):
    """List LLM models for the authenticated user."""
    return await llm_service.get_user_llm_models(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/{llm_model_id}", response_model=LLMModel)
async def get_llm_model(
    llm_model_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Retrieve an LLM model by ID."""
    llm_model = await llm_service.get_llm_model_by_id(
        db=db,
        llm_model_id=llm_model_id,
        user_id=current_user.id,
    )

    if not llm_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM model not found",
        )

    return llm_model


@router.put("/{llm_model_id}", response_model=LLMModel)
async def update_llm_model(
    llm_model_id: str,
    llm_data: LLMModelUpdate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Update an LLM model."""
    llm_model = await llm_service.update_llm_model(
        db=db,
        llm_model_id=llm_model_id,
        user_id=current_user.id,
        llm_data=llm_data,
    )

    if not llm_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM model not found",
        )

    return llm_model


@router.delete("/{llm_model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_model(
    llm_model_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Delete an LLM model."""
    success = await llm_service.delete_llm_model(
        db=db,
        llm_model_id=llm_model_id,
        user_id=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM model not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

