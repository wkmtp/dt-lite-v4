"""Tenant API Schemas - Pydantic models for Tenant CRUD."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    """Create tenant request."""
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    """Update tenant request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")
    metadata: Optional[dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: UUID
    name: str
    code: str
    status: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Paginated tenant list."""
    items: list[TenantResponse]
    total: int
    limit: int
    offset: int
