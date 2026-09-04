"""Provisioning Pydantic v2 schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProvisioningPlanCreateRequest(BaseModel):
    """Create a provisioning plan from a deployment instance."""

    deployment_instance_id: UUID = Field(..., description="Deployment instance to provision")

    @field_validator("deployment_instance_id")
    @classmethod
    def validate_uuid(cls, v):
        return v


class ProvisioningPlanResponse(BaseModel):
    """Response for provisioning plan."""

    id: UUID
    tenant_id: UUID
    deployment_instance_id: UUID
    status: str
    total_items: int
    completed_items: int
    error_summary: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ProvisioningItemResponse(BaseModel):
    """Response for provisioning item."""

    id: UUID
    plan_id: UUID
    template_id: Optional[UUID]
    entity_type_id: Optional[UUID]
    external_id: str
    action: str
    source_twin_id: Optional[UUID]
    target_twin_id: Optional[UUID]
    status: str
    created_twin_id: Optional[UUID]
    error_message: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class ProvisioningExecutionResponse(BaseModel):
    """Response for provisioning execution record."""

    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: str
    started_at: str
    finished_at: Optional[str]
    error_message: Optional[str]
    items_completed: int
    items_failed: int

    model_config = {"from_attributes": True}


class PlanValidationRequest(BaseModel):
    """Validate a deployment instance before planning."""

    deployment_instance_id: UUID


class PlanValidationResponse(BaseModel):
    """Validation result."""

    valid: bool
    issues: list[dict] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    passed_requirements: list[str] = Field(default_factory=list)
