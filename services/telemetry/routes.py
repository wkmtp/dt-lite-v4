"""Telemetry API Routes - Ingestion and query endpoints.

All routes enforce tenant isolation via TenantContext middleware.
POST /telemetry requires: telemetry:create permission
GET /telemetry requires: telemetry:read permission
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.telemetry.exceptions import (
    TelemetryDeviceNotFoundError,
    TelemetryTenantMismatchError,
    TelemetryValidationError,
)
from services.telemetry.schemas import (
    TelemetryBatchCreate,
    TelemetryPointCreate,
    TelemetryPointResponse,
    TelemetryQueryResponse,
)
from services.telemetry.services import TelemetryIngestionService
from services.telemetry.query_service import TelemetryQueryService

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.post(
    "/",
    response_model=TelemetryPointResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("telemetry:create"))],
)
async def ingest_telemetry(
    data: TelemetryPointCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Ingest a single telemetry point.

    Security:
    - tenant_id comes from JWT/TenantContext, NOT from request body
    - device_id and datapoint_id ownership verified against current tenant
    """
    async with AsyncSessionLocal() as db:
        service = TelemetryIngestionService(db)

        # Build NormalizedTelemetry from request
        from services.iota.contracts import NormalizedTelemetry
        telemetry = NormalizedTelemetry(
            tenant_id=str(tenant_id),
            device_id=str(data.device_id),
            datapoint_id=str(data.datapoint_id),
            event_time=data.event_time,
            ingested_at=data.ingested_at,
            value=data.value,
            data_type=data.data_type,
            unit=data.unit,
            quality=data.quality,
            metadata=data.metadata,
        )

        try:
            result = await service.ingest(telemetry, tenant_id)
        except TelemetryValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": e.code, "message": e.message},
            )
        except TelemetryDeviceNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": e.code, "message": e.message},
            )
        except TelemetryTenantMismatchError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": e.code, "message": e.message},
            )

    return TelemetryPointResponse(
        id=result.id,
        device_id=result.device_id,
        datapoint_id=result.datapoint_id,
        event_time=result.event_time,
        ingested_at=result.ingested_at,
        value=result.value,
        data_type=result.data_type,
        unit=result.unit,
        quality=result.quality,
        metadata=result.metadata or {},
    )


@router.post(
    "/batch",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("telemetry:create"))],
)
async def ingest_batch(
    data: TelemetryBatchCreate,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Ingest multiple telemetry points atomically.

    All points must pass validation or the entire batch rolls back.
    """
    async with AsyncSessionLocal() as db:
        service = TelemetryIngestionService(db)

        # Convert request to NormalizedTelemetry objects
        telemetries = []
        for p in data.points:
            from services.iota.contracts import NormalizedTelemetry
            telemetries.append(NormalizedTelemetry(
                tenant_id=str(tenant_id),
                device_id=str(p.device_id),
                datapoint_id=str(p.datapoint_id),
                event_time=p.event_time,
                ingested_at=p.ingested_at,
                value=p.value,
                data_type=p.data_type,
                unit=p.unit,
                quality=p.quality,
                metadata=p.metadata,
            ))

        try:
            count = await service.ingest_batch(telemetries, tenant_id)
        except TelemetryValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": e.code, "message": e.message},
            )
        except TelemetryDeviceNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": e.code, "message": e.message},
            )
        except TelemetryTenantMismatchError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": e.code, "message": e.message},
            )

    return {"success": True, "data": {"ingested_count": count}}


@router.get(
    "/device/{device_id}",
    response_model=TelemetryQueryResponse,
    dependencies=[Depends(require_permission("telemetry:read"))],
)
async def query_by_device(
    device_id: UUID,
    start_time: Optional[datetime] = Query(None, description="Start of time range (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="End of time range (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Query telemetry by device with time range filter."""
    async with AsyncSessionLocal() as db:
        service = TelemetryQueryService(db)
        return await service.query_by_device(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/datapoint/{datapoint_id}",
    response_model=TelemetryQueryResponse,
    dependencies=[Depends(require_permission("telemetry:read"))],
)
async def query_by_datapoint(
    datapoint_id: UUID,
    start_time: Optional[datetime] = Query(None, description="Start of time range (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="End of time range (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Query telemetry by datapoint with time range filter."""
    async with AsyncSessionLocal() as db:
        service = TelemetryQueryService(db)
        return await service.query_by_datapoint(
            datapoint_id=datapoint_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/range",
    response_model=TelemetryQueryResponse,
    dependencies=[Depends(require_permission("telemetry:read"))],
)
async def query_range(
    start_time: datetime = Query(..., description="Start of time range (ISO 8601)"),
    end_time: datetime = Query(..., description="End of time range (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Query all telemetry in a time range for current tenant."""
    async with AsyncSessionLocal() as db:
        service = TelemetryQueryService(db)
        return await service.query_range(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
