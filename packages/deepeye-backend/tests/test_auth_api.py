"""Tests for authentication API endpoints."""

import pytest
from fastapi import status
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.database.user import PasswordResetToken, User
from app.services.user_service import UserService


class TestAuthAPI:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client, db_session, test_user_data):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user_data["username"],
                "email": test_user_data["email"],
                "password": test_user_data["password"],
                "full_name": test_user_data["full_name"],
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client, db_session, test_user_data):
        """Test registration with duplicate username."""
        # Register first user
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user_data["username"],
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        # Try to register with same username
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user_data["username"],
                "email": "different@example.com",
                "password": "TestPassword123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client, db_session, test_user_data):
        """Test registration with duplicate email."""
        # Register first user
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user_data["username"],
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        # Try to register with same email
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": "differentuser",
                "email": test_user_data["email"],
                "password": "TestPassword123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_data(self, async_client):
        """Test registration with invalid data."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": "",  # Empty username
                "email": "invalid-email",  # Invalid email
                "password": "123",  # Too short password
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_success(self, async_client, db_session, test_user_data):
        """Test successful login."""
        # Register user first
        service = UserService()
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client, db_session, test_user_data):
        """Test login with wrong password."""
        # Register user first
        service = UserService()
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Try to login with wrong password
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client):
        """Test login with nonexistent user."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "TestPassword123",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client, db_session, test_user_data):
        """Test getting current user info."""
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

        # Get current user
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user.id
        assert data["username"] == user.username
        assert data["email"] == user.email

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, async_client):
        """Test getting current user without token."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client):
        """Test getting current user with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_change_password_success(self, async_client, db_session, test_user_data):
        """Test successful password change."""
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

        # Change password
        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": test_user_data["password"],
                "new_password": "NewPassword123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Password changed successfully" in response.json()["message"]

        # Verify new password works
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": "NewPassword123",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, async_client, db_session, test_user_data):
        """Test password change with wrong old password."""
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

        # Try to change password with wrong old password
        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "WrongPassword123",
                "new_password": "NewPassword123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Old password is incorrect" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, async_client, db_session, test_user_data, mocker):
        """Test successful password reset request."""
        # Register user
        service = UserService()
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Mock email sending
        mocker.patch("app.services.user_service.send_email")

        # Request password reset
        response = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": test_user_data["email"]},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "verification code has been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_reset_password_success(self, async_client, db_session, test_user_data, mocker):
        """Test successful password reset."""
        # Register user
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Mock email sending
        mocker.patch("app.services.user_service.send_email")

        # Request password reset
        await service.request_password_reset(db=db_session, email=test_user_data["email"])

        # Get the reset code
        stmt = select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()
        reset_code = token.code

        # Reset password
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": test_user_data["email"],
                "code": reset_code,
                "new_password": "NewPassword123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Password reset successfully" in response.json()["message"]

        # Verify new password works
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": "NewPassword123",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reset_password_invalid_code(self, async_client, db_session, test_user_data, mocker):
        """Test password reset with invalid code."""
        # Register user
        service = UserService()
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Mock email sending
        mocker.patch("app.services.user_service.send_email")

        # Request password reset
        await service.request_password_reset(db=db_session, email=test_user_data["email"])

        # Try to reset with invalid code
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": test_user_data["email"],
                "code": "000000",
                "new_password": "NewPassword123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired verification code" in response.json()["detail"]

