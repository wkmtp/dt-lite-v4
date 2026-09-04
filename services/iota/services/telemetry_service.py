"""Telemetry Normalization Service - Normalizes adapter output to internal format."""
from datetime import datetime, timezone
from uuid import UUID

from services.iota.contracts import DataType, DataQuality, NormalizedTelemetry


class TelemetryNormalizationService:
    """Normalizes telemetry data from protocol adapters."""

    @classmethod
    def normalize(cls, raw_data: dict, tenant_id: UUID, device_id: UUID) -> NormalizedTelemetry:
        """Normalize raw adapter output to NormalizedTelemetry.

        Args:
            raw_data: Raw data from adapter (may contain protocol-specific fields)
            tenant_id: Tenant context
            device_id: Device that produced the data

        Returns:
            NormalizedTelemetry instance
        """
        datapoint_id = raw_data.get("datapoint_id", raw_data.get("external_id", ""))
        event_time = raw_data.get("event_time")
        ingested_at = datetime.now(timezone.utc)

        # Parse event_time if provided as string
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                event_time = ingested_at
        elif event_time is None:
            event_time = ingested_at

        # Ensure timezone-aware
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        value = raw_data.get("value")
        data_type = raw_data.get("data_type", DataType.STRING.value)
        unit = raw_data.get("unit")
        quality = raw_data.get("quality", DataQuality.GOOD.value)

        telemetry = NormalizedTelemetry(
            tenant_id=str(tenant_id),
            device_id=str(device_id),
            datapoint_id=str(datapoint_id),
            event_time=event_time,
            ingested_at=ingested_at,
            value=value,
            data_type=data_type,
            unit=unit,
            quality=quality,
            metadata=raw_data.get("metadata", {}),
        )

        errors = telemetry.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        return telemetry
