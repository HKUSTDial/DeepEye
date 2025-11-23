"""LLM model service."""

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database.llm import LLMModel
from app.models.schemas.llm import LLMModelCreate, LLMModelUpdate


class LLMService:
    """Service for managing LLM models."""

    async def create_llm_model(
        self,
        db: AsyncSession,
        user_id: str,
        llm_data: LLMModelCreate,
    ) -> LLMModel:
        """Create a new LLM model."""
        llm_model = LLMModel(
            user_id=user_id,
            base_url=llm_data.base_url,
            api_key=llm_data.api_key,
            model_endpoint_name=llm_data.model_endpoint_name,
            model_name=llm_data.model_name,
        )

        db.add(llm_model)
        await db.commit()
        await db.refresh(llm_model)

        return llm_model

    async def get_llm_model_by_id(
        self, db: AsyncSession, llm_model_id: str, user_id: Optional[str] = None
    ) -> Optional[LLMModel]:
        """Get LLM model by ID."""
        stmt = select(LLMModel).where(LLMModel.id == llm_model_id)
        
        # If user_id is provided, ensure the LLM model belongs to the user
        if user_id:
            stmt = stmt.where(LLMModel.user_id == user_id)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_llm_models(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[LLMModel]:
        """Get all LLM models for a user."""
        stmt = (
            select(LLMModel)
            .where(LLMModel.user_id == user_id)
            .order_by(LLMModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_llm_model(
        self,
        db: AsyncSession,
        llm_model_id: str,
        user_id: str,
        llm_data: LLMModelUpdate,
    ) -> Optional[LLMModel]:
        """Update an LLM model."""
        llm_model = await self.get_llm_model_by_id(db, llm_model_id, user_id)
        
        if not llm_model:
            return None

        # Update fields if provided
        update_data = llm_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(llm_model, field, value)

        await db.commit()
        await db.refresh(llm_model)

        return llm_model

    async def delete_llm_model(
        self, db: AsyncSession, llm_model_id: str, user_id: str
    ) -> bool:
        """Delete an LLM model."""
        llm_model = await self.get_llm_model_by_id(db, llm_model_id, user_id)
        
        if not llm_model:
            return False

        stmt = delete(LLMModel).where(LLMModel.id == llm_model_id)
        await db.execute(stmt)
        await db.commit()

        return True

