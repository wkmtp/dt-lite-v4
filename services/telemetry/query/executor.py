"""Query Executor — Executes TelemetryQuery against the repository."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.telemetry.query.dsl import Aggregate, TelemetryQuery
from services.telemetry.repositories import TelemetryRepository

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executes telemetry queries with push-down aggregation support."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = TelemetryRepository(session)

    async def execute(self, query: TelemetryQuery) -> dict:
        """Execute a telemetry query."""
        errors = query.validate()
        if errors:
            return {"error": errors, "data": [], "total": 0}

        target_table = query.get_target_table()
        logger.debug("Executing query on table: %s", target_table)

        # Build base query
        stmt = select("*").where(
            # Time range filter
            # Asset filter
            # Property filter
            # Quality filter
        )

        # Apply aggregation if not RAW
        if query.aggregate != Aggregate.RAW:
            stmt = stmt.group_by(
                # bucket/aggregation column
                # asset_id
                # property_code
            )

        # Apply pagination
        stmt = stmt.offset(query.offset).limit(query.limit)
        stmt = stmt.order_by("event_time DESC")  # or appropriate column

        # Execute
        result = await self._session.execute(stmt)
        rows = result.fetchall()

        return {
            "data": [self._row_to_dict(row) for row in rows],
            "total": len(rows),
            "aggregate": query.aggregate.value,
            "timerange": {
                "start": query.timerange.start.isoformat(),
                "end": query.timerange.end.isoformat(),
            },
        }

    def _row_to_dict(self, row) -> dict:
        """Convert a row to a dictionary."""
        return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
