"""Tenant DTO Schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    """Request schema for creating a tenant."""
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    """Request schema for updating a tenant."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")
    metadata: Optional[dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Response schema for tenant."""
    id: UUID
    name: str
    code: str
    status: str
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Paginated list response."""
    items: list[TenantResponse]
    total: int
    limit: int
    offset: int
