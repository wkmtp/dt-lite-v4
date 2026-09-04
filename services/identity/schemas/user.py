"""User DTO Schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Request schema for creating a user."""
    tenant_id: UUID
    username: str = Field(..., min_length=1, max_length=128)
    email: Optional[str] = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8)
    role_codes: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Request schema for updating a user."""
    email: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")
    metadata: Optional[dict[str, Any]] = None


class UserResponse(BaseModel):
    """Response schema for user."""
    id: UUID
    tenant_id: UUID
    username: str
    email: Optional[str] = None
    status: str
    roles: list[dict[str, Any]] = []
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list response."""
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str
    tenant_code: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
