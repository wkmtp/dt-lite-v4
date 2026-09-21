"""Telemetry Ingestion Service - Validates and persists NormalizedTelemetry.

This service is the bridge between Adapter Runtime and Persistence:
1. Receives NormalizedTelemetry from AdapterRuntime
2. Validates tenant ownership (device_id, datapoint_id belong to current tenant)
3. Normalizes timestamps to UTC
4. Persists via TelemetryRepository

Security:
- tenant_id comes ONLY from TenantContext (never from client request body)
- device_id/datapoint_id ownership verified against current tenant via repositories
- No adapter control, no protocol coupling
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.iota.contracts import NormalizedTelemetry
from services.iota.repositories.device_repository import DeviceRepository
from services.iota.repositories.data_point_repository import DataPointRepository
from services.telemetry.exceptions import (
    TelemetryDeviceNotFoundError,
    TelemetryTenantMismatchError,
    TelemetryValidationError,
)
from services.telemetry.models import TelemetryPoint
from services.telemetry.repositories import TelemetryRepository

logger = logging.getLogger(__name__)


class TelemetryIngestionService:
    """Validates and persists normalized telemetry data.

    Responsibility:
    - Receive NormalizedTelemetry from Adapter Runtime
    - Validate tenant context
    - Verify device/datapoint ownership
    - Normalize timestamps to UTC
    - Persist via TelemetryRepository

    Does NOT:
    - Control adapters
    - Parse protocols
    - Implement business rules
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._telemetry_repo = TelemetryRepository(session)
        self._device_repo = DeviceRepository(session)
        self._datapoint_repo = DataPointRepository(session)

    async def ingest(
        self,
        telemetry: NormalizedTelemetry,
        tenant_id: UUID,
    ) -> TelemetryPoint:
        """Ingest a single telemetry point.

        Args:
            telemetry: NormalizedTelemetry from adapter.
            tenant_id: Current tenant UUID from TenantContext.

        Returns:
            Saved TelemetryPoint.

        Raises:
            TelemetryValidationError: If validation fails.
            TelemetryTenantMismatchError: If device/datapoint doesn't belong to tenant.
            TelemetryDeviceNotFoundError: If device not found.
        """
        # Validate telemetry
        errors = telemetry.validate()
        if errors:
            raise TelemetryValidationError(errors)

        # Ensure timestamps are UTC-aware
        event_time = self._ensure_utc(telemetry.event_time)
        ingested_at = self._ensure_utc(telemetry.ingested_at)

        # Verify device belongs to tenant
        device = await self._device_repo.get_by_id_for_tenant(
            UUID(telemetry.device_id), tenant_id
        )
        if device is None:
            raise TelemetryDeviceNotFoundError(str(telemetry.device_id))

        # Verify datapoint belongs to tenant and is linked to this device
        datapoint = await self._datapoint_repo.get_by_id_for_tenant(
            UUID(telemetry.datapoint_id), tenant_id
        )
        if datapoint is None:
            raise TelemetryTenantMismatchError(
                str(tenant_id), f"Datapoint {telemetry.datapoint_id} not found"
            )

        # Create persistent record
        point = TelemetryPoint(
            tenant_id=tenant_id,
            device_id=UUID(telemetry.device_id),
            datapoint_id=UUID(telemetry.datapoint_id),
            event_time=event_time,
            ingested_at=ingested_at,
            value=telemetry.value,
            data_type=telemetry.data_type,
            unit=telemetry.unit,
            quality=telemetry.quality,
            meta_data=telemetry.metadata or {},
        )

        saved = await self._telemetry_repo.save(point)
        logger.info(
            "Ingested telemetry: device=%s datapoint=%s value=%s",
            telemetry.device_id,
            telemetry.datapoint_id,
            telemetry.value,
        )
        return saved

    async def ingest_batch(
        self,
        telemetries: list[NormalizedTelemetry],
        tenant_id: UUID,
    ) -> int:
        """Ingest multiple telemetry points atomically.

        All points must pass validation or the entire batch rolls back.

        Args:
            telemetries: List of NormalizedTelemetry.
            tenant_id: Current tenant UUID from TenantContext.

        Returns:
            Number of points successfully ingested.

        Raises:
            TelemetryValidationError: If any point fails validation.
            TelemetryTenantMismatchError: If ownership check fails.
        """
        if not telemetries:
            return 0

        # Pre-validate all points
        for i, t in enumerate(telemetries):
            errors = t.validate()
            if errors:
                raise TelemetryValidationError(
                    [f"[{i}] {'; '.join(errors)}"]
                )

        # Pre-check all device/datapoint ownership
        device_ids = {str(t.device_id) for t in telemetries}
        datapoint_ids = {str(t.datapoint_id) for t in telemetries}

        # Verify each device belongs to tenant
        for device_id in device_ids:
            device = await self._device_repo.get_by_id_for_tenant(
                UUID(device_id), tenant_id
            )
            if device is None:
                raise TelemetryDeviceNotFoundError(device_id)

        # Verify each datapoint belongs to tenant
        for datapoint_id in datapoint_ids:
            datapoint = await self._datapoint_repo.get_by_id_for_tenant(
                UUID(datapoint_id), tenant_id
            )
            if datapoint is None:
                raise TelemetryTenantMismatchError(
                    str(tenant_id), f"Datapoint {datapoint_id} not found"
                )

        # Build persistence records
        points = []
        for t in telemetries:
            points.append(TelemetryPoint(
                tenant_id=tenant_id,
                device_id=UUID(t.device_id),
                datapoint_id=UUID(t.datapoint_id),
                event_time=self._ensure_utc(t.event_time),
                ingested_at=self._ensure_utc(t.ingested_at),
                value=t.value,
                data_type=t.data_type,
                unit=t.unit,
                quality=t.quality,
                meta_data=t.metadata or {},
            ))

        count = await self._telemetry_repo.save_batch(points)
        logger.info("Batch ingested %d telemetry points for tenant %s", count, tenant_id)
        return count

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware UTC.

        Args:
            dt: Input datetime (may be naive or different timezone).

        Returns:
            UTC-aware datetime.
        """
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            return dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if in different timezone
        return dt.astimezone(timezone.utc)
