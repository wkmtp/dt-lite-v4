"""Relationship DTO Schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RelationshipCreate(BaseModel):
    """Request schema for creating a relationship."""
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: str = Field(..., min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipResponse(BaseModel):
    """Response schema for a relationship."""
    id: UUID
    tenant_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: str
    extra_data: dict[str, Any]
    created_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RelationshipListResponse(BaseModel):
    """Paginated list response."""
    items: list[RelationshipResponse]
    total: int
    limit: int
    offset: int
