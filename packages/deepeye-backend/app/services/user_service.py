"""User service."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.database.user import PasswordResetToken, User
from app.utils.email import send_email


class UserService:
    """User service for managing user operations."""

    async def register_user(
        self,
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        """Register a new user."""
        # Check if username already exists
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Check if email already exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("Email already exists")

        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    async def authenticate_user(
        self, db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """Authenticate a user."""
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await db.get(User, user_id)

    async def change_password(
        self, db: AsyncSession, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """Change user password."""
        user = await db.get(User, user_id)
        if not user:
            return False

        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Old password is incorrect")

        # Update password
        user.hashed_password = get_password_hash(new_password)
        await db.commit()

        return True

    async def request_password_reset(self, db: AsyncSession, email: str) -> bool:
        """Request password reset (send verification code)."""
        # Find user
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # For security, return True even if user doesn't exist
            return True

        # Generate 6-digit verification code
        code = str(secrets.randbelow(900000) + 100000)  # 100000 - 999999

        # Save verification code (valid for 15 minutes)
        reset_token = PasswordResetToken(
            user_id=user.id,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )

        db.add(reset_token)
        await db.commit()

        # Send email
        await send_email(
            to=email,
            subject="DeepEye 密码重置验证码",
            body=f"您的验证码是：{code}\n\n该验证码将在 15 分钟后过期。",
        )

        return True

    async def reset_password(
        self, db: AsyncSession, email: str, code: str, new_password: str
    ) -> bool:
        """Reset password using verification code."""
        # Find user
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Verify code
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.code == code,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()

        if not token:
            raise ValueError("Invalid or expired verification code")

        # Update password
        user.hashed_password = get_password_hash(new_password)
        token.used = True

        await db.commit()

        return True

