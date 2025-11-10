"""Tests for user service."""

import pytest
from sqlalchemy import select

from app.models.database.user import PasswordResetToken, User
from app.services.user_service import UserService


class TestUserService:
    """Test UserService class."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, db_session, test_user_data):
        """Test successful user registration."""
        service = UserService()
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            full_name=test_user_data["full_name"],
        )

        assert user is not None
        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
        assert user.full_name == test_user_data["full_name"]
        assert user.is_active is True
        assert user.hashed_password != test_user_data["password"]  # Should be hashed

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, db_session, test_user_data):
        """Test registration with duplicate username."""
        service = UserService()

        # Register first user
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Try to register with same username
        with pytest.raises(ValueError, match="Username already exists"):
            await service.register_user(
                db=db_session,
                username=test_user_data["username"],
                email="different@example.com",
                password="TestPassword123",
            )

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, db_session, test_user_data):
        """Test registration with duplicate email."""
        service = UserService()

        # Register first user
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Try to register with same email
        with pytest.raises(ValueError, match="Email already exists"):
            await service.register_user(
                db=db_session,
                username="differentuser",
                email=test_user_data["email"],
                password="TestPassword123",
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, test_user_data):
        """Test successful user authentication."""
        service = UserService()

        # Register user
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Authenticate
        authenticated_user = await service.authenticate_user(
            db=db_session,
            username=test_user_data["username"],
            password=test_user_data["password"],
        )

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.username == user.username

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, test_user_data):
        """Test authentication with wrong password."""
        service = UserService()

        # Register user
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Try to authenticate with wrong password
        authenticated_user = await service.authenticate_user(
            db=db_session,
            username=test_user_data["username"],
            password="WrongPassword123",
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with nonexistent user."""
        service = UserService()

        authenticated_user = await service.authenticate_user(
            db=db_session,
            username="nonexistent",
            password="TestPassword123",
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, db_session, test_user_data):
        """Test authentication with inactive user."""
        service = UserService()

        # Register user
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Deactivate user
        user.is_active = False
        await db_session.commit()

        # Try to authenticate
        authenticated_user = await service.authenticate_user(
            db=db_session,
            username=test_user_data["username"],
            password=test_user_data["password"],
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, test_user_data):
        """Test getting user by ID."""
        service = UserService()

        # Register user
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Get user by ID
        retrieved_user = await service.get_user_by_id(db=db_session, user_id=user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username

    @pytest.mark.asyncio
    async def test_get_user_by_id_nonexistent(self, db_session):
        """Test getting nonexistent user by ID."""
        service = UserService()

        retrieved_user = await service.get_user_by_id(
            db=db_session, user_id="nonexistent-id"
        )

        assert retrieved_user is None

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session, test_user_data):
        """Test successful password change."""
        service = UserService()

        # Register user
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        old_password_hash = user.hashed_password

        # Change password
        result = await service.change_password(
            db=db_session,
            user_id=user.id,
            old_password=test_user_data["password"],
            new_password="NewPassword123",
        )

        assert result is True

        # Refresh user and verify password changed
        await db_session.refresh(user)
        assert user.hashed_password != old_password_hash

        # Verify new password works
        authenticated_user = await service.authenticate_user(
            db=db_session,
            username=test_user_data["username"],
            password="NewPassword123",
        )
        assert authenticated_user is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, db_session, test_user_data):
        """Test password change with wrong old password."""
        service = UserService()

        # Register user
        user = await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Try to change password with wrong old password
        with pytest.raises(ValueError, match="Old password is incorrect"):
            await service.change_password(
                db=db_session,
                user_id=user.id,
                old_password="WrongPassword123",
                new_password="NewPassword123",
            )

    @pytest.mark.asyncio
    async def test_change_password_nonexistent_user(self, db_session):
        """Test password change for nonexistent user."""
        service = UserService()

        result = await service.change_password(
            db=db_session,
            user_id="nonexistent-id",
            old_password="OldPassword123",
            new_password="NewPassword123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, db_session, test_user_data, mocker):
        """Test successful password reset request."""
        service = UserService()

        # Register user
        await service.register_user(
            db=db_session,
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
        )

        # Mock email sending
        mock_send_email = mocker.patch("app.services.user_service.send_email")

        # Request password reset
        result = await service.request_password_reset(
            db=db_session, email=test_user_data["email"]
        )

        assert result is True

        # Verify token was created
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id.in_(
                select(User.id).where(User.email == test_user_data["email"])
            )
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()

        assert token is not None
        assert token.code is not None
        assert len(token.code) == 6
        assert token.used is False

        # Verify email was sent
        mock_send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(self, db_session, mocker):
        """Test password reset request for nonexistent email."""
        service = UserService()

        # Mock email sending
        mock_send_email = mocker.patch("app.services.user_service.send_email")

        # Request password reset for nonexistent email
        result = await service.request_password_reset(
            db=db_session, email="nonexistent@example.com"
        )

        # Should return True for security (don't reveal if email exists)
        assert result is True

        # Email should not be sent
        mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db_session, test_user_data, mocker):
        """Test successful password reset."""
        service = UserService()

        # Register user
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
        reset_result = await service.reset_password(
            db=db_session,
            email=test_user_data["email"],
            code=reset_code,
            new_password="NewPassword123",
        )

        assert reset_result is True

        # Verify password was changed
        authenticated_user = await service.authenticate_user(
            db=db_session,
            username=test_user_data["username"],
            password="NewPassword123",
        )
        assert authenticated_user is not None

        # Verify token was marked as used
        await db_session.refresh(token)
        assert token.used is True

    @pytest.mark.asyncio
    async def test_reset_password_invalid_code(self, db_session, test_user_data, mocker):
        """Test password reset with invalid code."""
        service = UserService()

        # Register user
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
        with pytest.raises(ValueError, match="Invalid or expired verification code"):
            await service.reset_password(
                db=db_session,
                email=test_user_data["email"],
                code="000000",
                new_password="NewPassword123",
            )

    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_email(self, db_session):
        """Test password reset with nonexistent email."""
        service = UserService()

        with pytest.raises(ValueError, match="User not found"):
            await service.reset_password(
                db=db_session,
                email="nonexistent@example.com",
                code="123456",
                new_password="NewPassword123",
            )

