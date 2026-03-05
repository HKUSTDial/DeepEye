"""Auth API schemas."""

from pydantic import BaseModel, EmailStr


class AuthUser(BaseModel):
    id: str
    email: EmailStr
    username: str
    is_superuser: bool
    is_email_verified: bool = False


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GenericMessageResponse(BaseModel):
    message: str
    debug_token: str | None = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr


class VerifyEmailConfirmRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str
