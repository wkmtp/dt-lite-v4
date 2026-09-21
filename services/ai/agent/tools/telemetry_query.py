"""TelemetryQueryTool — wraps the Telemetry API for agent access.

Provides read-only access to historical telemetry data scoped to the
calling tenant. All queries are routed through the Gateway so the
agent never calls the Telemetry service directly.

Uses the TelemetryQuery DSL from services.telemetry.query.dsl for
unified query building and validation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config
from services.telemetry.query.dsl import (
    Aggregate,
    TelemetryQuery,
    TimeRange,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class TelemetryPoint(BaseModel):
    """A single telemetry data point."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    value: float = Field(..., description="Telemetry value")
    quality: str = Field("GOOD", description="Data quality indicator")
    entity_id: Optional[str] = Field(None, description="Associated entity ID")
    property_code: Optional[str] = Field(None, description="Property code")


class TelemetryQueryResult(BaseModel):
    """Structured result from a telemetry query."""
    success: bool = True
    total: int = Field(0, description="Total matching points")
    limit: int = Field(100, description="Requested limit")
    offset: int = Field(0, description="Pagination offset")
    has_more: bool = Field(False, description="Whether more pages exist")
    points: list[TelemetryPoint] = Field(default_factory=list)
    aggregation: str = Field("raw", description="Aggregation level used")
    time_range: dict[str, str] = Field(default_factory=dict)
    query_id: Optional[str] = Field(None, description="Query execution ID")
    error: Optional[str] = Field(None, description="Error message if any")


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class TelemetryQueryTool:
    """Query historical telemetry data via the Gateway API.

    Tool name: ``telemetry_query``

    Input schema::

        {
            "device_id": "<uuid>",
            "datapoint_id": "<uuid>",
            "entity_id": "<uuid>",
            "property_code": "temperature",
            "start_time": "<ISO-8601>",
            "end_time": "<ISO-8601>",
            "aggregate": "raw|1m|1h|1d",
            "limit": 100,
            "offset": 0,
            "quality_filter": "GOOD|UNCERTAIN|BAD"
        }
    """

    tool_name = "telemetry_query"
    description = (
        "Query historical telemetry data for devices, entities, or properties "
        "within a time range. Supports aggregation (raw, 1m, 1h, 1d), quality "
        "filtering, and pagination. Returns time-series data with timestamps, "
        "values, and quality indicators. All queries are scoped to the current tenant."
    )

    AGGREGATE_VALUES = {"raw", "1m", "1h", "1d"}
    QUALITY_VALUES = {"GOOD", "UNCERTAIN", "BAD"}

    def __init__(self, tenant_id: str, config: Optional[AIConfig] = None) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()
        self._client = httpx.AsyncClient(
            base_url=self.config.GATEWAY_URL,
            timeout=30.0,
        )

    async def execute(
        self,
        tenant_id: str,
        device_id: Optional[str] = None,
        datapoint_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        property_code: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        aggregate: str = "raw",
        limit: int = 100,
        offset: int = 0,
        quality_filter: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a telemetry query.

        Args:
            tenant_id: Caller's tenant (validated against self.tenant_id).
            device_id: Optional device UUID to filter by.
            datapoint_id: Optional datapoint UUID to filter by.
            entity_id: Optional entity UUID for entity-scoped queries.
            property_code: Optional property code (e.g., "temperature").
            start_time: Optional ISO-8601 start of time range.
            end_time: Optional ISO-8601 end of time range.
            aggregate: Aggregation level: raw, 1m, 1h, or 1d.
            limit: Max results (default 100, max 10000 for raw).
            offset: Pagination offset (default 0).
            quality_filter: Optional quality filter: GOOD, UNCERTAIN, BAD.
            **kwargs: Ignored extra parameters.

        Returns:
            Dict with total, points, pagination info, and query metadata.
        """
        # Tenant validation
        if tenant_id != self.tenant_id:
            return {
                "success": False,
                "error": "tenant_mismatch",
                "message": "Access denied: tenant ID mismatch",
            }

        # Validate aggregate
        if aggregate not in self.AGGREGATE_VALUES:
            return {
                "success": False,
                "error": "invalid_aggregate",
                "message": f"aggregate must be one of {self.AGGREGATE_VALUES}",
            }

        # Validate quality_filter
        if quality_filter and quality_filter not in self.QUALITY_VALUES:
            return {
                "success": False,
                "error": "invalid_quality_filter",
                "message": f"quality_filter must be one of {self.QUALITY_VALUES}",
            }

        # Validate limit for raw queries
        if aggregate == "raw" and limit > 10000:
            return {
                "success": False,
                "error": "limit_too_large",
                "message": "RAW queries limited to 10000 points",
            }

        # Parse time range
        parsed_start: Optional[datetime] = None
        parsed_end: Optional[datetime] = None
        if start_time:
            try:
                parsed_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return {
                    "success": False,
                    "error": "invalid_start_time",
                    "message": f"Invalid start_time format: {start_time}",
                }
        if end_time:
            try:
                parsed_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return {
                    "success": False,
                    "error": "invalid_end_time",
                    "message": f"Invalid end_time format: {end_time}",
                }

        # Validate time range
        if parsed_start and parsed_end and parsed_start > parsed_end:
            return {
                "success": False,
                "error": "invalid_time_range",
                "message": "start_time must be before end_time",
            }

        # Build query params
        params: dict[str, Any] = {
            "limit": str(limit),
            "offset": str(offset),
            "aggregate": aggregate,
        }
        if device_id:
            params["device_id"] = device_id
        if datapoint_id:
            params["datapoint_id"] = datapoint_id
        if entity_id:
            params["entity_id"] = entity_id
        if property_code:
            params["property_code"] = property_code
        if quality_filter:
            params["quality_filter"] = quality_filter
        if parsed_start:
            params["start_time"] = parsed_start.isoformat()
        if parsed_end:
            params["end_time"] = parsed_end.isoformat()

        # Also build a DSL query for validation (client-side)
        dsl_errors: list[str] = []
        if parsed_start and parsed_end:
            try:
                time_range = TimeRange(start=parsed_start, end=parsed_end)
                errors = time_range.validate()
                dsl_errors.extend(errors)
            except Exception as exc:
                dsl_errors.append(str(exc))

        if dsl_errors:
            return {
                "success": False,
                "error": "validation_failed",
                "message": "; ".join(dsl_errors),
            }

        try:
            resp = await self._client.get(
                "/api/v1/telemetry/query",
                params=params,
                headers={
                    "X-Tenant-ID": self.tenant_id,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Parse response points
            raw_points = data.get("points", data.get("data", []))
            points = []
            for pt in raw_points:
                points.append(TelemetryPoint(
                    timestamp=pt.get("timestamp", pt.get("event_time", "")),
                    value=float(pt.get("value", 0)),
                    quality=pt.get("quality", "GOOD"),
                    entity_id=pt.get("entity_id"),
                    property_code=pt.get("property_code", property_code),
                ))

            total = data.get("total", data.get("count", len(points)))
            query_id = data.get("query_id", data.get("id"))

            result = TelemetryQueryResult(
                success=True,
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit < total),
                points=points,
                aggregation=aggregate,
                time_range={
                    "start": start_time or "now-1h",
                    "end": end_time or "now",
                },
                query_id=query_id,
            )
            return result.model_dump()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_detail = exc.response.text if exc.response.text else str(exc)

            if status_code == 404:
                logger.warning("Telemetry query 404: %s", error_detail)
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"Telemetry data not found for the given filters",
                    "details": error_detail,
                }
            elif status_code == 400:
                logger.warning("Telemetry query 400: %s", error_detail)
                return {
                    "success": False,
                    "error": "bad_request",
                    "message": f"Invalid telemetry query: {error_detail}",
                    "details": error_detail,
                }
            elif status_code == 429:
                logger.warning("Telemetry query 429 (rate limited): %s", error_detail)
                return {
                    "success": False,
                    "error": "rate_limited",
                    "message": "Telemetry query rate limited, please retry",
                    "retry_after": exc.response.headers.get("Retry-After", "60"),
                }
            elif status_code == 500:
                logger.error("Telemetry query 500: %s", error_detail)
                return {
                    "success": False,
                    "error": "internal_error",
                    "message": "Telemetry service internal error",
                    "details": error_detail,
                }
            else:
                logger.warning("Telemetry query HTTP error %d: %s", status_code, error_detail)
                return {
                    "success": False,
                    "error": f"http_{status_code}",
                    "message": f"Telemetry query failed with status {status_code}",
                    "details": error_detail,
                }
        except httpx.TimeoutException:
            logger.error("Telemetry query timeout after 30s")
            return {
                "success": False,
                "error": "timeout",
                "message": "Telemetry query timed out after 30 seconds",
            }
        except httpx.ConnectError as exc:
            logger.error("Telemetry query connection error: %s", exc)
            return {
                "success": False,
                "error": "connection_error",
                "message": f"Failed to connect to telemetry service: {exc}",
            }
        except Exception as exc:
            logger.error("Telemetry query unexpected error: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": "unexpected_error",
                "message": f"Unexpected error during telemetry query: {exc}",
            }

    async def query_by_time_range(
        self,
        tenant_id: str,
        start_time: str,
        end_time: str,
        aggregate: str = "raw",
        limit: int = 1000,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience method for time-range queries.

        Args:
            tenant_id: Caller's tenant.
            start_time: ISO-8601 start time.
            end_time: ISO-8601 end time.
            aggregate: Aggregation level.
            limit: Max results.
            offset: Pagination offset.
            **kwargs: Additional filter parameters.

        Returns:
            TelemetryQueryResult as dict.
        """
        return await self.execute(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            aggregate=aggregate,
            limit=limit,
            offset=offset,
            **kwargs,
        )

    async def query_latest(
        self,
        tenant_id: str,
        device_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        property_code: Optional[str] = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience method for querying the latest telemetry points.

        Args:
            tenant_id: Caller's tenant.
            device_id: Optional device UUID.
            entity_id: Optional entity UUID.
            property_code: Optional property code.
            limit: Max results (default 100).
            **kwargs: Additional parameters.

        Returns:
            TelemetryQueryResult with latest points.
        """
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=1)).isoformat()
        return await self.execute(
            tenant_id=tenant_id,
            device_id=device_id,
            entity_id=entity_id,
            property_code=property_code,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            **kwargs,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "TelemetryQueryTool":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
