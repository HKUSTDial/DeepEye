"""Tests for dependencies."""

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import create_access_token
from app.dependencies import get_current_user
from app.models.database.user import User
from app.services.user_service import UserService


class TestDependencies:
    """Test dependency injection functions."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db_session, test_user_data):
        """Test successful get_current_user."""
        # Register user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Create token
        token = create_access_token(data={"sub": user.id})

        # Create credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Get current user
        current_user = await get_current_user(
            credentials=credentials,
            db=db_session,
        )

        assert current_user is not None
        assert current_user.id == user.id
        assert current_user.username == user.username

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        """Test get_current_user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self, db_session):
        """Test get_current_user with nonexistent user ID."""
        # Create token with nonexistent user ID
        token = create_access_token(data={"sub": "nonexistent-id"})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found or inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, db_session, test_user_data):
        """Test get_current_user with inactive user."""
        # Register user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Deactivate user
        user.is_active = False
        await db_session.commit()

        # Create token
        token = create_access_token(data={"sub": user.id})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found or inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self, db_session):
        """Test get_current_user with token missing 'sub' claim."""
        # Create token without 'sub'
        token = create_access_token(data={"other": "value"})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication credentials" in exc_info.value.detail

