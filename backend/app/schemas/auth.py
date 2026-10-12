from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MembershipStatus, SystemRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    membership_status: MembershipStatus
    system_role: SystemRole
    is_active: bool
    permissions: list[str] = []


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


TokenResponse.model_rebuild()
