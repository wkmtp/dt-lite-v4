"""Ontology Pydantic schemas for API request/response validation."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Ontology Concept Schemas
# ---------------------------------------------------------------------------

class ConceptCreateRequest(BaseModel):
    """Request body for creating an ontology concept."""
    code: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="general", max_length=64)
    parent_id: Optional[UUID] = Field(None, description="Parent concept ID (null for root)")
    description: Optional[str] = Field(None, max_length=2000)
    version: str = Field(default="1.0.0", max_length=32)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("code cannot be empty")
        return v.strip().lower()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"general", "physical", "logical", "spatial", "temporal", "behavioral"}
        if v.lower() not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v.lower()


class ConceptUpdateRequest(BaseModel):
    """Request body for updating an ontology concept."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    parent_id: Optional[UUID] = Field(None)


class ConceptResponse(BaseModel):
    """Response model for an ontology concept."""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    category: str
    parent_id: Optional[UUID]
    description: Optional[str]
    version: str
    children_count: int = 0
    entity_types_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Entity Type Definition Schemas
# ---------------------------------------------------------------------------

class EntityTypeCreateRequest(BaseModel):
    """Request body for creating an entity type definition."""
    ontology_id: UUID = Field(..., description="Parent ontology concept ID")
    code: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = Field(None, max_length=64)
    property_schema: dict[str, Any] = Field(default_factory=dict)
    allowed_capabilities: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("code cannot be empty")
        return v.strip().lower()


class EntityTypeUpdateRequest(BaseModel):
    """Request body for updating an entity type definition."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = Field(None, max_length=64)
    property_schema: Optional[dict[str, Any]] = None
    allowed_capabilities: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|archived)$")


class EntityTypeResponse(BaseModel):
    """Response model for an entity type definition."""
    id: UUID
    tenant_id: UUID
    ontology_id: UUID
    code: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    property_schema: dict[str, Any]
    allowed_capabilities: dict[str, Any]
    status: str
    capabilities_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Capability Definition Schemas
# ---------------------------------------------------------------------------

class CapabilityCreateRequest(BaseModel):
    """Request body for creating a capability definition."""
    code: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    schema_definition: dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="1.0.0", max_length=32)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("code cannot be empty")
        # Capability codes use PascalCase (e.g., TemperatureMeasurement)
        if not v[0].isupper():
            raise ValueError("capability code must start with uppercase letter (PascalCase)")
        return v.strip()


class CapabilityUpdateRequest(BaseModel):
    """Request body for updating a capability definition."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    schema_definition: Optional[dict[str, Any]] = None
    version: Optional[str] = Field(None, max_length=32)


class CapabilityResponse(BaseModel):
    """Response model for a capability definition."""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: Optional[str]
    schema_definition: dict[str, Any]
    version: str
    properties_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Semantic Property Schemas
# ---------------------------------------------------------------------------

VALID_DATA_TYPES = {"string", "integer", "float", "boolean", "datetime", "json"}


class SemanticPropertyCreateRequest(BaseModel):
    """Request body for adding a semantic property to a capability."""
    name: str = Field(..., min_length=1, max_length=128)
    data_type: str = Field(..., max_length=32)
    unit: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=500)
    required: bool = Field(default=False)

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
        return v.strip().lower()


class SemanticPropertyResponse(BaseModel):
    """Response model for a semantic property."""
    id: UUID
    capability_id: UUID
    name: str
    data_type: str
    unit: Optional[str]
    description: Optional[str]
    required: bool
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Template Capability Binding Schemas
# ---------------------------------------------------------------------------

class TemplateCapabilityBindRequest(BaseModel):
    """Request body for binding a capability to a template."""
    template_id: UUID
    capability_id: UUID
    required: bool = Field(default=True)


class TemplateCapabilityBindingResponse(BaseModel):
    """Response model for a template-capability binding."""
    id: UUID
    template_id: UUID
    capability_id: UUID
    required: bool
    capability_code: str
    capability_name: str
    created_at: str

    model_config = {"from_attributes": True}
