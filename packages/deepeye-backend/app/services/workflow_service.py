"""Workflow service."""

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database.workflow import Workflow
from app.models.schemas.workflow import WorkflowCreate, WorkflowUpdate


class WorkflowService:
    """Workflow service for managing workflow operations."""

    async def create_workflow(
        self,
        db: AsyncSession,
        user_id: str,
        workflow_data: WorkflowCreate,
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            user_id=user_id,
            name=workflow_data.name,
            description=workflow_data.description,
            version=workflow_data.version,
            author=workflow_data.author,
            tags=workflow_data.tags,
            workflow_data=workflow_data.workflow_data,
        )

        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        return workflow

    async def get_workflow_by_id(
        self, db: AsyncSession, workflow_id: str, user_id: Optional[str] = None
    ) -> Optional[Workflow]:
        """Get workflow by ID."""
        stmt = select(Workflow).where(Workflow.id == workflow_id)
        
        # If user_id is provided, ensure the workflow belongs to the user
        if user_id:
            stmt = stmt.where(Workflow.user_id == user_id)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_workflows(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Workflow]:
        """Get all workflows for a user."""
        stmt = (
            select(Workflow)
            .where(Workflow.user_id == user_id)
            .order_by(Workflow.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        user_id: str,
        workflow_data: WorkflowUpdate,
    ) -> Optional[Workflow]:
        """Update a workflow."""
        workflow = await self.get_workflow_by_id(db, workflow_id, user_id)
        
        if not workflow:
            return None

        # Update fields if provided
        if workflow_data.name is not None:
            workflow.name = workflow_data.name
        if workflow_data.description is not None:
            workflow.description = workflow_data.description
        if workflow_data.version is not None:
            workflow.version = workflow_data.version
        if workflow_data.author is not None:
            workflow.author = workflow_data.author
        if workflow_data.tags is not None:
            workflow.tags = workflow_data.tags
        if workflow_data.workflow_data is not None:
            workflow.workflow_data = workflow_data.workflow_data

        await db.commit()
        await db.refresh(workflow)

        return workflow

    async def delete_workflow(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> bool:
        """Delete a workflow."""
        workflow = await self.get_workflow_by_id(db, workflow_id, user_id)
        
        if not workflow:
            return False

        stmt = delete(Workflow).where(Workflow.id == workflow_id)
        await db.execute(stmt)
        await db.commit()

        return True

