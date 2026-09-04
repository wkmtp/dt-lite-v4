"""Deployment Pydantic schemas for API request/response validation."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Deployment Profile Schemas
# ---------------------------------------------------------------------------

class DeploymentProfileCreateRequest(BaseModel):
    """Request body for creating a deployment profile."""

    name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(default="general", max_length=64)
    template_id: UUID = Field(..., description="Parent twin template ID")
    description: Optional[str] = Field(None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        return v.strip().lower()


class DeploymentProfileUpdateRequest(BaseModel):
    """Request body for updating a deployment profile."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")


class DeploymentProfileResponse(BaseModel):
    """Response model for a deployment profile."""

    id: UUID
    tenant_id: UUID
    name: str
    industry: str
    template_id: UUID
    description: Optional[str]
    status: str
    instance_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Deployment Instance Schemas
# ---------------------------------------------------------------------------

VALID_INSTANCE_STATUSES = {
    "draft", "validating", "ready", "deployed", "running", "offline", "archived"
}


class DeploymentInstanceCreateRequest(BaseModel):
    """Request body for creating a deployment instance."""

    profile_id: UUID = Field(..., description="Parent deployment profile ID")
    name: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=512)
    status: str = Field(default="draft", pattern="^draft$|^validating$|^ready$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class DeploymentInstanceResponse(BaseModel):
    """Response model for a deployment instance."""

    id: UUID
    tenant_id: UUID
    profile_id: UUID
    name: str
    location: Optional[str]
    status: str
    node_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Deployment Node Schemas
# ---------------------------------------------------------------------------

class DeploymentNodeCreateRequest(BaseModel):
    """Request body for creating a deployment node."""

    name: str = Field(..., min_length=1, max_length=255)
    node_type: str = Field(default="generic", max_length=128)
    entity_type_id: Optional[UUID] = Field(None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        return v.strip().lower()


class DeploymentNodeResponse(BaseModel):
    """Response model for a deployment node."""

    id: UUID
    tenant_id: UUID
    deployment_id: UUID
    name: str
    node_type: str
    entity_type_id: Optional[UUID]
    capability_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Deployment Node Capability Schemas
# ---------------------------------------------------------------------------

class DeploymentNodeCapabilityBindRequest(BaseModel):
    """Request body for binding a capability to a deployment node."""

    capability_id: UUID
    configuration_schema: dict[str, Any] = Field(default_factory=dict)
    required: bool = Field(default=True)


class DeploymentNodeCapabilityResponse(BaseModel):
    """Response model for a deployment node capability binding."""

    id: UUID
    node_id: UUID
    capability_id: UUID
    configuration_schema: dict[str, Any]
    required: bool
    capability_code: str
    capability_name: str
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Validation Response
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    """A single validation issue."""

    severity: str  # "error" or "warning"
    message: str
    field: Optional[str] = None


class DeploymentValidationResponse(BaseModel):
    """Response model for deployment validation."""

    valid: bool
    issues: list[ValidationIssue] = []
    missing_capabilities: list[str] = []
    passed_requirements: list[str] = []
