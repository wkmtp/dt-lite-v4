"""User API Schemas - Pydantic models for User CRUD."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Create user request."""
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=8)
    email: Optional[str] = Field(default=None, max_length=255)
    role_codes: list[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    tenant_id: UUID
    username: str
    email: Optional[str] = None
    status: str
    roles: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated user list."""
    items: list[UserResponse]
    total: int
    limit: int
    offset: int
