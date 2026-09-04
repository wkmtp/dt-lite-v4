"""Template Pydantic schemas for API request/response validation."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Template schemas
# ---------------------------------------------------------------------------

class TemplateCreateRequest(BaseModel):
    """Request body for creating a new template."""

    code: str = Field(..., min_length=1, max_length=128, description="Unique template code")
    name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(default="general", max_length=64)
    version: str = Field(default="1.0.0", max_length=32)
    description: Optional[str] = Field(None, max_length=1000)
    schema_definition: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("code cannot be empty")
        v = v.strip().lower()
        # Code format: section.subsection... (e.g., building.hvac.ahu)
        parts = v.split(".")
        if len(parts) < 2:
            raise ValueError("code must contain at least one dot (e.g., building.hvac.ahu)")
        for part in parts:
            if not part or not part[0].isalpha():
                raise ValueError(f"code part '{part}' must start with a letter")
        return v

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        allowed = {"building", "factory", "energy", "campus", "water", "general"}
        if v.lower() not in allowed:
            raise ValueError(f"industry must be one of {allowed}, got '{v}'")
        return v.lower()


class TemplateUpdateRequest(BaseModel):
    """Request body for updating a template."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    schema_definition: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|archived)$")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.lower()
        return v


class TemplateResponse(BaseModel):
    """Response model for a template."""

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    industry: str
    version: str
    description: Optional[str]
    schema_definition: dict[str, Any]
    status: str
    properties_count: int = 0
    relationships_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Property schemas
# ---------------------------------------------------------------------------

VALID_DATA_TYPES = {"string", "integer", "float", "boolean", "datetime", "json"}


class PropertyCreateRequest(BaseModel):
    """Request body for adding a property to a template."""

    name: str = Field(..., min_length=1, max_length=128)
    data_type: str = Field(..., max_length=32)
    unit: Optional[str] = Field(None, max_length=64)
    required: bool = Field(default=False)
    default_value: Optional[Any] = None

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        v = v.lower()
        if v not in VALID_DATA_TYPES:
            raise ValueError(f"data_type must be one of {VALID_DATA_TYPES}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class PropertyResponse(BaseModel):
    """Response model for a template property."""

    id: UUID
    template_id: UUID
    name: str
    data_type: str
    unit: Optional[str]
    required: bool
    default_value: Optional[Any]
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Relationship schemas
# ---------------------------------------------------------------------------

class RelationshipCreateRequest(BaseModel):
    """Request body for defining an allowed relationship."""

    relationship_type: str = Field(..., min_length=1, max_length=64)
    target_template: Optional[str] = Field(None, max_length=128)

    @field_validator("relationship_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("relationship_type cannot be empty")
        return v.strip().lower()


class RelationshipResponse(BaseModel):
    """Response model for a template relationship."""

    id: UUID
    template_id: UUID
    relationship_type: str
    target_template: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}
