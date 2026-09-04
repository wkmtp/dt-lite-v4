"""Telemetry Layer - Time-series data ingestion and query.

Receives NormalizedTelemetry from Adapter Runtime, validates tenant ownership,
and persists to PostgreSQL time-series storage.

Architecture:
    AdapterRuntime → TelemetryIngestionService → TelemetryRepository → DB
                                                  ↓
                                              TelemetryQueryService

Security:
    - tenant_id comes from TenantContext (never from client request body)
    - device_id/datapoint_id ownership verified against current tenant
    - No adapter control, no protocol coupling, no industry logic
"""