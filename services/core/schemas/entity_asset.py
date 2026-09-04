from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    tenant_id: str
    entity_type: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    name: str
    description: Optional[str]
    status: str
    properties: Dict[str, Any] = {}
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AssetCreate(BaseModel):
    entity_id: str
    asset_code: str = Field(..., min_length=1, max_length=128)
    asset_class: str = Field(..., min_length=1, max_length=128)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    lifecycle_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    id: str
    entity_id: str
    asset_code: str
    asset_class: str
    lifecycle_status: str
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PropertyDefinitionCreate(BaseModel):
    tenant_id: Optional[str] = None
    entity_type: str
    key: str
    data_type: str = Field(..., pattern="^(string|integer|number|boolean|datetime|json)$")
    unit: Optional[str] = None
    required: bool = False
    writable: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyValueUpdate(BaseModel):
    value: Any


class RelationshipCreate(BaseModel):
    tenant_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str = Field(..., min_length=1, max_length=128)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelationshipResponse(BaseModel):
    id: str
    tenant_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    created_at: str

    class Config:
        from_attributes = True
