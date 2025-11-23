"""Database connection API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.dependencies import CurrentUserDep, DatabaseDep
from app.models.schemas.connection import (
    DatabaseConnection,
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
)
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/database-connections", tags=["database-connections"])

connection_service = ConnectionService()


@router.post("", response_model=DatabaseConnection, status_code=status.HTTP_201_CREATED)
async def create_database_connection(
    connection_data: DatabaseConnectionCreate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Create a new database connection for the authenticated user."""
    connection = await connection_service.create_connection(
        db=db,
        user_id=current_user.id,
        connection_data=connection_data,
    )
    return connection


@router.get("", response_model=List[DatabaseConnection])
async def list_database_connections(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    skip: int = Query(0, ge=0, description="Number of connections to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of connections to return"),
):
    """List database connections for the authenticated user."""
    return await connection_service.get_user_connections(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/{connection_id}", response_model=DatabaseConnection)
async def get_database_connection(
    connection_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Retrieve a single database connection."""
    connection = await connection_service.get_connection_by_id(
        db=db,
        connection_id=connection_id,
        user_id=current_user.id,
    )
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found",
        )

    return connection


@router.put("/{connection_id}", response_model=DatabaseConnection)
async def update_database_connection(
    connection_id: str,
    connection_data: DatabaseConnectionUpdate,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Update an existing database connection."""
    connection = await connection_service.update_connection(
        db=db,
        connection_id=connection_id,
        user_id=current_user.id,
        connection_data=connection_data,
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found",
        )

    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database_connection(
    connection_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep,
):
    """Delete a database connection."""
    success = await connection_service.delete_connection(
        db=db,
        connection_id=connection_id,
        user_id=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

