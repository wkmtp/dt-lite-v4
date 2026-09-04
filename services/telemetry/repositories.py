"""Telemetry Repository - Time-series data persistence layer."""
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.telemetry.models import TelemetryPoint


class TelemetryRepository(TenantAwareRepository[TelemetryPoint]):
    """Repository for time-series telemetry data.

    Telemetry is append-only historical data — no soft delete.
    Inherits TenantAwareRepository for automatic tenant filtering.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TelemetryPoint)

    async def save(self, point: TelemetryPoint) -> TelemetryPoint:
        """Persist a single telemetry point.

        Args:
            point: TelemetryPoint to save.

        Returns:
            Saved TelemetryPoint with ID populated.
        """
        self.session.add(point)
        await self.session.flush()
        await self.session.refresh(point)
        return point

    async def save_batch(self, points: list[TelemetryPoint]) -> int:
        """Batch insert telemetry points within a transaction.

        Args:
            points: List of TelemetryPoint instances.

        Returns:
            Number of points inserted.

        Raises:
            Exception: All points rolled back if any fail.
        """
        if not points:
            return 0
        self.session.add_all(points)
        await self.session.flush()
        return len(points)

    async def query_by_device(
        self,
        device_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TelemetryPoint]:
        """Query telemetry by device with optional time range.

        Args:
            device_id: Device identifier.
            start_time: Optional start of time range (inclusive).
            end_time: Optional end of time range (inclusive).
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Ordered sequence of telemetry points.
        """
        stmt = select(TelemetryPoint).where(
            TelemetryPoint.device_id == device_id,
        )

        # Apply tenant filter from context
        tenant_filter = self._get_tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        if start_time:
            stmt = stmt.where(TelemetryPoint.event_time >= start_time)
        if end_time:
            stmt = stmt.where(TelemetryPoint.event_time <= end_time)

        stmt = stmt.order_by(TelemetryPoint.event_time.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def query_by_datapoint(
        self,
        datapoint_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TelemetryPoint]:
        """Query telemetry by datapoint with optional time range.

        Args:
            datapoint_id: DataPoint identifier.
            start_time: Optional start of time range (inclusive).
            end_time: Optional end of time range (inclusive).
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Ordered sequence of telemetry points.
        """
        stmt = select(TelemetryPoint).where(
            TelemetryPoint.datapoint_id == datapoint_id,
        )

        tenant_filter = self._get_tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        if start_time:
            stmt = stmt.where(TelemetryPoint.event_time >= start_time)
        if end_time:
            stmt = stmt.where(TelemetryPoint.event_time <= end_time)

        stmt = stmt.order_by(TelemetryPoint.event_time.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def query_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TelemetryPoint]:
        """Query all telemetry in a time range for current tenant.

        Args:
            start_time: Start of time range (inclusive).
            end_time: End of time range (inclusive).
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Ordered sequence of telemetry points.
        """
        stmt = select(TelemetryPoint).where(
            TelemetryPoint.event_time >= start_time,
            TelemetryPoint.event_time <= end_time,
        )

        tenant_filter = self._get_tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        stmt = stmt.order_by(TelemetryPoint.event_time.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, device_id: Optional[UUID] = None) -> int:
        """Count telemetry points, optionally filtered by device.

        Args:
            device_id: Optional device filter.

        Returns:
            Count of matching points.
        """
        stmt = select(func.count()).select_from(TelemetryPoint)

        tenant_filter = self._get_tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        if device_id:
            stmt = stmt.where(TelemetryPoint.device_id == device_id)

        result = await self.session.execute(stmt)
        return result.scalar_one()
