"""Activation layer Pydantic v2 schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class TwinActivationLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    twin_entity_id: UUID
    state: str
    binding_id: Optional[UUID] = None
    error_message: Optional[str] = None
    activated_at: Optional[str] = None
    deactivated_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @field_validator("activated_at", mode="before")
    @classmethod
    def serialize_activated_at(cls, v: Any) -> Optional[str]:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    @field_validator("deactivated_at", mode="before")
    @classmethod
    def serialize_deactivated_at(cls, v: Any) -> Optional[str]:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class TwinCommandResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    twin_binding_id: UUID
    target_device_id: UUID
    command_type: str
    payload: dict[str, Any]
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    executed_at: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator("executed_at", mode="before")
    @classmethod
    def serialize_executed_at(cls, v: Any) -> Optional[str]:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class TwinActivationStatusResponse(BaseModel):
    entity_id: UUID
    tenant_id: UUID
    state: str
    binding_id: Optional[UUID] = None
    activated_at: Optional[str] = None
    error_message: Optional[str] = None
