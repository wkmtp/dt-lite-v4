"""Entity DTO Schemas - Data Transfer Objects for Entity service."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    """Request schema for creating an entity."""
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    """Request schema for updating an entity."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=512)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")
    extra_data: Optional[dict[str, Any]] = None


class EntityResponse(BaseModel):
    """Response schema for entity."""
    id: UUID
    tenant_id: UUID
    entity_type: str
    name: str
    description: Optional[str] = None
    status: str
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EntityListResponse(BaseModel):
    """Paginated list response."""
    items: list[EntityResponse]
    total: int
    limit: int
    offset: int
