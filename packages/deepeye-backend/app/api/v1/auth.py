"""Authentication API routes."""

from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.dependencies import CurrentUserDep, DatabaseDep
from app.models.schemas.user import (
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserProfile,
    UserRegister,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

user_service = UserService()


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: DatabaseDep):
    """Register a new user."""
    try:
        user = await user_service.register_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: DatabaseDep):
    """Login and get access token."""
    user = await user_service.authenticate_user(
        db=db, username=credentials.username, password=credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.id})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1440 * 60,  # seconds
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_info(current_user: CurrentUserDep):
    """Get current user information."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange, current_user: CurrentUserDep, db: DatabaseDep
):
    """Change user password."""
    try:
        await user_service.change_password(
            db=db,
            user_id=current_user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password,
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(reset_request: PasswordResetRequest, db: DatabaseDep):
    """Request password reset (send verification code)."""
    await user_service.request_password_reset(db=db, email=reset_request.email)
    return {"message": "If the email exists, a verification code has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(reset_data: PasswordReset, db: DatabaseDep):
    """Reset password using verification code."""
    try:
        await user_service.reset_password(
            db=db,
            email=reset_data.email,
            code=reset_data.code,
            new_password=reset_data.new_password,
        )
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

