"""TwinGraph Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RelationshipCreateRequest(BaseModel):
    """Request body for creating a twin relationship."""

    source_id: UUID = Field(..., description="Source twin entity ID")
    target_id: UUID = Field(..., description="Target twin entity ID")
    relationship_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$',
        description="Semantic relationship type (e.g., contains, located_in, controls)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("relationship_type cannot be empty")
        return v.strip()


class RelationshipResponse(BaseModel):
    """Response model for a twin relationship."""

    id: UUID
    tenant_id: UUID
    source_id: UUID
    target_id: UUID
    relationship_type: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NeighborResponse(BaseModel):
    """Response for a neighbor in the twin graph."""

    twin_id: UUID
    relationship_type: str
    direction: str  # "outgoing" or "incoming"

    model_config = {"from_attributes": True}


class PathStep(BaseModel):
    """A single step in a graph path."""

    entity_id: UUID
    relationship_type: str
    direction: str  # "forward" or "reverse"


class PathResponse(BaseModel):
    """Response for a path query result."""

    source_id: UUID
    target_id: UUID
    path: list[dict[str, Any]]
    depth: int

    model_config = {"from_attributes": True}
