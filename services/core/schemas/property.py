"""Property DTO Schemas - Data Transfer Objects for Property service."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Valid property data types
VALID_PROPERTY_TYPES = {"STRING", "INTEGER", "FLOAT", "BOOLEAN", "JSON"}


class PropertyDefinitionCreate(BaseModel):
    """Request schema for creating a property definition."""
    entity_type: str = Field(..., min_length=1, max_length=128)
    key: str = Field(..., min_length=1, max_length=128)
    data_type: str = Field(..., pattern="^(STRING|INTEGER|FLOAT|BOOLEAN|JSON)$")
    unit: Optional[str] = Field(default=None, max_length=32)
    required: bool = False
    writable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PropertyValueSet(BaseModel):
    """Request schema for setting a property value."""
    value: Any  # Type validated by service based on definition


class PropertyDefinitionResponse(BaseModel):
    """Response schema for property definition."""
    id: UUID
    tenant_id: Optional[UUID] = None
    entity_type: str
    key: str
    data_type: str
    unit: Optional[str] = None
    required: bool
    writable: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PropertyValueResponse(BaseModel):
    """Response schema for property value."""
    entity_id: UUID
    definition_id: UUID
    value: Optional[dict[str, Any]] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListResponse(BaseModel):
    """Paginated list response."""
    items: list[PropertyDefinitionResponse]
    total: int
    limit: int
    offset: int
