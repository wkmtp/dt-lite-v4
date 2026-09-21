"""Adapter API routes — FastAPI endpoints for adapter management."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from services.auth.dependencies import get_current_tenant, require_permission
from services.adapter.health import AdapterHealthChecker
from services.adapter.matching import CapabilityAdapterMatcher
from services.adapter.models import CapabilityMatch
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime
from services.adapter.services import AdapterService

router = APIRouter(prefix="/api/v1/adapters", tags=["Adapter"])

_registry = AdapterRegistry()
_runtime = AdapterRuntime()
_health_checker = AdapterHealthChecker()
_matcher = CapabilityAdapterMatcher()


def _get_service() -> AdapterService:
    return AdapterService(_registry, _runtime, _health_checker, _matcher)


def _create_adapter_instance(adapter_id: UUID, adapter_type: str):
    if adapter_type == "bacnet":
        from services.adapter.bacnet import BACnetAdapter
        return BACnetAdapter(adapter_id)
    elif adapter_type == "modbus":
        from services.adapter.modbus import ModbusAdapter
        return ModbusAdapter(adapter_id)
    elif adapter_type == "mqtt":
        from services.adapter.mqtt import MQTTAdapter
        return MQTTAdapter(adapter_id)
    elif adapter_type == "opcua":
        from services.adapter.opcua import OPCUAAdapter
        return OPCUAAdapter(adapter_id)
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("adapter:create"))])
async def register_adapter(adapter_id: UUID, adapter_type: str,
                            tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        adapter = _create_adapter_instance(adapter_id, adapter_type)
        await service.register_adapter(adapter_id, tenant_id, adapter)
        return {"status": "registered", "adapter_id": str(adapter_id), "type": adapter_type}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "REGISTER_ERROR", "message": str(e)})


@router.delete("/{adapter_id}", dependencies=[Depends(require_permission("adapter:delete"))])
async def unregister_adapter(adapter_id: UUID, tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        await service.unregister_adapter(adapter_id, tenant_id)
        return {"status": "unregistered"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "UNREGISTER_ERROR", "message": str(e)})


@router.post("/{adapter_id}/connect", dependencies=[Depends(require_permission("adapter:connect"))])
async def connect_adapter(adapter_id: UUID, request: dict,
                           tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        await service.connect_adapter(adapter_id, tenant_id, request.get("endpoint"), request.get("credentials_ref"), request.get("config", {}))
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "CONNECT_ERROR", "message": str(e)})


@router.post("/{adapter_id}/disconnect", dependencies=[Depends(require_permission("adapter:disconnect"))])
async def disconnect_adapter(adapter_id: UUID, tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        await service.disconnect_adapter(adapter_id, tenant_id)
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "DISCONNECT_ERROR", "message": str(e)})


@router.get("/{adapter_id}/health", dependencies=[Depends(require_permission("adapter:read"))])
async def get_adapter_health(adapter_id: UUID, tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        status = await service.check_health(adapter_id, tenant_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "HEALTH_ERROR", "message": str(e)})


@router.post("/{adapter_id}/read", response_model=dict, dependencies=[Depends(require_permission("adapter:read"))])
async def read_from_adapter(adapter_id: UUID, request: dict,
                             tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        external_ids = request.get("external_ids", [])
        telemetry = await service.read_data(adapter_id, tenant_id, external_ids)
        return {"count": len(telemetry), "data": [t.model_dump() for t in telemetry]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "READ_ERROR", "message": str(e)})


@router.post("/{adapter_id}/write", response_model=dict, dependencies=[Depends(require_permission("adapter:write"))])
async def write_to_adapter(adapter_id: UUID, request: dict,
                            tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        success = await service.write_data(adapter_id, tenant_id, request.get("external_id"), request.get("value"), request.get("data_type", "FLOAT"))
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "WRITE_ERROR", "message": str(e)})


@router.post("/{adapter_id}/subscribe", response_model=dict, dependencies=[Depends(require_permission("adapter:subscribe"))])
async def subscribe_to_adapter(adapter_id: UUID, request: dict,
                                tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    try:
        sub_id = await service.subscribe_data(adapter_id, tenant_id, request.get("external_id"), None)
        return {"subscription_id": sub_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "SUBSCRIBE_ERROR", "message": str(e)})


@router.post("/match", response_model=list[CapabilityMatch], dependencies=[Depends(require_permission("adapter:read"))])
async def match_capabilities(capability_key: str, data_type: str = "FLOAT",
                              unit: Optional[str] = None,
                              semantic_tags: Optional[list[str]] = None,
                              required_capabilities: Optional[list[str]] = None,
                              tenant_id: UUID = Depends(get_current_tenant)):
    service = _get_service()
    matches = await service.match_capability(capability_key, data_type, unit, semantic_tags, required_capabilities)
    return matches
