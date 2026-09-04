"""Asset DTO Schemas - Data Transfer Objects for Asset service."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    """Request schema for creating an asset."""
    entity_id: UUID
    asset_code: str = Field(..., min_length=1, max_length=128)
    asset_class: str = Field(..., min_length=1, max_length=128)
    manufacturer: Optional[str] = Field(default=None, max_length=255)
    model: Optional[str] = Field(default=None, max_length=255)
    serial_number: Optional[str] = Field(default=None, max_length=255)
    installed_at: Optional[datetime] = None
    extra_data: dict[str, Any] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    """Request schema for updating an asset."""
    manufacturer: Optional[str] = Field(default=None, max_length=255)
    model: Optional[str] = Field(default=None, max_length=255)
    serial_number: Optional[str] = Field(default=None, max_length=255)
    installed_at: Optional[datetime] = None
    extra_data: Optional[dict[str, Any]] = None


class AssetResponse(BaseModel):
    """Response schema for asset."""
    id: UUID
    entity_id: UUID
    asset_code: str
    asset_class: str
    lifecycle_status: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installed_at: Optional[datetime] = None
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    """Paginated list response."""
    items: list[AssetResponse]
    total: int
    limit: int
    offset: int
