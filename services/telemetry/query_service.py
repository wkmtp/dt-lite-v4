"""Telemetry Query Service - Time-range and device-based queries.

Provides read access to historical telemetry data with automatic tenant filtering.
All queries are scoped to the current tenant context — no cross-tenant access possible.
"""
import logging
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.telemetry.models import TelemetryPoint
from services.telemetry.repositories import TelemetryRepository
from services.telemetry.schemas import TelemetryPointResponse, TelemetryQueryResponse

logger = logging.getLogger(__name__)


class TelemetryQueryService:
    """Read-only service for querying historical telemetry data.

    All queries automatically filter by current tenant context.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = TelemetryRepository(session)

    async def query_by_device(
        self,
        device_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> TelemetryQueryResponse:
        """Query telemetry points by device ID.

        Args:
            device_id: Target device UUID.
            start_time: Optional start of time range (inclusive).
            end_time: Optional end of time range (inclusive).
            limit: Max results (default 100).
            offset: Pagination offset (default 0).

        Returns:
            TelemetryQueryResponse with points and metadata.
        """
        points = await self._repo.query_by_device(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return TelemetryQueryResponse(
            total=len(points),
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            points=[self._to_response(p) for p in points],
        )

    async def query_by_datapoint(
        self,
        datapoint_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> TelemetryQueryResponse:
        """Query telemetry points by datapoint ID.

        Args:
            datapoint_id: Target datapoint UUID.
            start_time: Optional start of time range (inclusive).
            end_time: Optional end of time range (inclusive).
            limit: Max results (default 100).
            offset: Pagination offset (default 0).

        Returns:
            TelemetryQueryResponse with points and metadata.
        """
        points = await self._repo.query_by_datapoint(
            datapoint_id=datapoint_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return TelemetryQueryResponse(
            total=len(points),
            datapoint_id=datapoint_id,
            start_time=start_time,
            end_time=end_time,
            points=[self._to_response(p) for p in points],
        )

    async def query_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> TelemetryQueryResponse:
        """Query all telemetry in a time range for current tenant.

        Args:
            start_time: Start of time range (inclusive).
            end_time: End of time range (inclusive).
            limit: Max results (default 100).
            offset: Pagination offset (default 0).

        Returns:
            TelemetryQueryResponse with points and metadata.
        """
        points = await self._repo.query_range(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return TelemetryQueryResponse(
            total=len(points),
            start_time=start_time,
            end_time=end_time,
            points=[self._to_response(p) for p in points],
        )

    @staticmethod
    def _to_response(point: TelemetryPoint) -> TelemetryPointResponse:
        """Convert TelemetryPoint to response schema."""
        return TelemetryPointResponse(
            id=point.id,
            device_id=point.device_id,
            datapoint_id=point.datapoint_id,
            event_time=point.event_time,
            ingested_at=point.ingested_at,
            value=point.value,
            data_type=point.data_type,
            unit=point.unit,
            quality=point.quality,
            metadata=point.meta_data or {},
        )
