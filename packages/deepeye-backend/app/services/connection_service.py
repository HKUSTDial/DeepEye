"""Database connection service."""

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database.connection import DatabaseConnection
from app.models.schemas.connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
)


class ConnectionService:
    """Service for managing database connections."""

    async def create_connection(
        self,
        db: AsyncSession,
        user_id: str,
        connection_data: DatabaseConnectionCreate,
    ) -> DatabaseConnection:
        """Create a new database connection."""
        connection = DatabaseConnection(
            user_id=user_id,
            name=connection_data.name,
            type=connection_data.type,
            host=connection_data.host,
            port=connection_data.port,
            username=connection_data.username,
            password=connection_data.password,
            database=connection_data.database,
        )

        db.add(connection)
        await db.commit()
        await db.refresh(connection)

        return connection

    async def get_connection_by_id(
        self, db: AsyncSession, connection_id: str, user_id: Optional[str] = None
    ) -> Optional[DatabaseConnection]:
        """Get database connection by ID."""
        stmt = select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        
        # If user_id is provided, ensure the connection belongs to the user
        if user_id:
            stmt = stmt.where(DatabaseConnection.user_id == user_id)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_connections(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[DatabaseConnection]:
        """Get all database connections for a user."""
        stmt = (
            select(DatabaseConnection)
            .where(DatabaseConnection.user_id == user_id)
            .order_by(DatabaseConnection.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_connection(
        self,
        db: AsyncSession,
        connection_id: str,
        user_id: str,
        connection_data: DatabaseConnectionUpdate,
    ) -> Optional[DatabaseConnection]:
        """Update a database connection."""
        connection = await self.get_connection_by_id(db, connection_id, user_id)
        
        if not connection:
            return None

        # Update fields if provided
        update_data = connection_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(connection, field, value)

        await db.commit()
        await db.refresh(connection)

        return connection

    async def delete_connection(
        self, db: AsyncSession, connection_id: str, user_id: str
    ) -> bool:
        """Delete a database connection."""
        connection = await self.get_connection_by_id(db, connection_id, user_id)
        
        if not connection:
            return False

        stmt = delete(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        await db.execute(stmt)
        await db.commit()

        return True

