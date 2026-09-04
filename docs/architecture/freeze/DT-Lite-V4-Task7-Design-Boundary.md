# DT-Lite V4.0 Phase 1 — Task 7 Design Boundary

**Document Version:** 1.0
**Date:** 2026-09-02
**Context:** Post Task 6 Freeze
**Purpose:** Define constraints for Telemetry Ingestion & Persistence Layer

---

## 1. Frozen Boundaries (DO NOT MODIFY)

### services/adapter/ (Task 6 - FROZEN)
```
services/adapter/
├── __init__.py       ← FROZEN
├── exceptions.py     ← FROZEN
├── models.py         ← FROZEN
├── registry.py       ← FROZEN
├── lifecycle.py      ← FROZEN
├── health.py         ← FROZEN
├── runtime.py        ← FROZEN
└── simulator.py      ← FROZEN
```

### services/iota/contracts.py (FROZEN)
- ProtocolAdapter ABC
- NormalizedTelemetry dataclass
- AdapterCapability enum
- DiscoveryResult dataclass
- SecretProvider ABC

### Test Baseline
- `tests/adapter/test_adapter_runtime.py` (45 tests) — DO NOT MODIFY

---

## 2. Task 7 Responsibilities

### Telemetry Pipeline
```
AdapterRuntime.read()
        ↓
NormalizedTelemetry (from Task 6)
        ↓
TelemetryIngestionService (Task 7 - NEW)
        ├── Validate tenant ownership
        ├── Verify device/datapoint belong to tenant
        ├── Normalize timestamps to UTC
        └── Persist via TelemetryRepository
                ↓
        telemetry_points table (new migration)
```

### Query Interface
```
GET /api/v1/telemetry/device/{id}
GET /api/v1/telemetry/datapoint/{id}
GET /api/v1/telemetry/range
        ↓
TelemetryQueryService (Task 7 - NEW)
        └── Return TelemetryPointResponse objects
```

---

## 3. Task 7 Constraints

### MUST CONSUME
- Input: `NormalizedTelemetry` from AdapterRuntime
- Tenant context from `TenantContext.get_tenant_id()`
- Device/DataPoint from IOTA repositories (read-only validation)

### MUST NOT MODIFY
- `services/adapter/` — Zero changes allowed
- `services/iota/models/` — No schema changes
- `services/core/` — No core service changes
- `NormalizedTelemetry` fields — Use as-is

### MUST IMPLEMENT
- `services/telemetry/models.py` — TelemetryPoint SQLAlchemy model
- `services/telemetry/repositories.py` — TelemetryRepository
- `services/telemetry/services.py` — TelemetryIngestionService
- `services/telemetry/query_service.py` — TelemetryQueryService
- `services/telemetry/schemas.py` — Pydantic DTOs
- `services/telemetry/exceptions.py` — Custom exceptions
- `services/telemetry/routes.py` — API endpoints
- `database/migrations/versions/phase6_telemetry.py` — Migration
- `tests/telemetry/` — Test suite

---

## 4. Data Flow Architecture

### Ingestion Path
```python
# Service layer pattern (NOT in adapter layer)
async def ingest_telemetry(tenant_id: UUID, connection_id: UUID, external_ids: list[str]):
    # 1. Get adapter from runtime (read-only access)
    telemetry_list = await runtime.read(connection_id, external_ids)
    
    # 2. Enrich with tenant context
    for t in telemetry_list:
        t.tenant_id = str(tenant_id)
    
    # 3. Validate and persist
    for telemetry in telemetry_list:
        await ingestion_service.ingest(telemetry, tenant_id)
```

### Query Path
```python
# Query service with automatic tenant filter
async def query_by_device(device_id: UUID, start_time: datetime, end_time: datetime):
    return await query_service.query_by_device(
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )
    # Tenant filter applied automatically by TelemetryRepository
```

---

## 5. Security Requirements

### Tenant Isolation (Critical)
```
✅ tenant_id comes from TenantContext (JWT → get_current_user → get_current_tenant)
❌ Client request body NEVER contains tenant_id
❌ Adapter layer NEVER stores tenant_id
```

### IDOR Protection
```
✅ Verify device belongs to current tenant before ingestion
✅ Verify datapoint belongs to current tenant before ingestion
✅ All queries scoped to TenantContext
❌ Cross-tenant access MUST fail
```

### Response Sanitization
```
✅ Return only: id, device_id, datapoint_id, event_time, value, metadata
❌ Never return: endpoint, credentials_ref, adapter info, connection details
```

---

## 6. Database Design

### New Table: telemetry_points
```sql
CREATE TABLE telemetry_points (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    datapoint_id UUID NOT NULL REFERENCES data_points(id) ON DELETE CASCADE,
    
    event_time TIMESTAMPTZ NOT NULL,      -- Device measurement time
    ingested_at TIMESTAMPTZ NOT NULL,     -- System receive time (UTC)
    
    value JSONB NOT NULL,                 -- Measurement value
    data_type VARCHAR(32) NOT NULL,       -- BOOLEAN/INTEGER/FLOAT/STRING/JSON
    unit VARCHAR(64),                     -- Physical unit
    quality VARCHAR(32) NOT NULL DEFAULT 'GOOD',
    metadata JSONB NOT NULL DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX ix_telemetry_tenant_device_time 
    ON telemetry_points(tenant_id, device_id, event_time);
CREATE INDEX ix_telemetry_datapoint_time 
    ON telemetry_points(datapoint_id, event_time);
CREATE INDEX ix_telemetry_tenant_time 
    ON telemetry_points(tenant_id, event_time);
```

### Design Notes
- Append-only historical data
- No soft delete (deleted_at column)
- CASCADE delete on device/datapoint removal
- Composite indexes for time-range queries

---

## 7. Repository Contract

### TelemetryRepository
```python
class TelemetryRepository(TenantAwareRepository[TelemetryPoint]):
    async def save(self, point: TelemetryPoint) -> TelemetryPoint
    async def save_batch(self, points: list[TelemetryPoint]) -> int
    async def query_by_device(self, device_id: UUID, ...) -> Sequence[TelemetryPoint]
    async def query_by_datapoint(self, datapoint_id: UUID, ...) -> Sequence[TelemetryPoint]
    async def query_range(self, start_time: datetime, end_time: datetime, ...) -> Sequence[TelemetryPoint]
    async def count(self, device_id: Optional[UUID] = None) -> int
```

### Forbidden Imports
```python
# TELEMETRY LAYER MUST NOT IMPORT:
from services.adapter import AdapterRuntime  # ❌
from services.core.repositories import ...  # ❌ (except base classes)
from services.iota.repositories import DeviceRepository  # ✅ OK for validation
```

---

## 8. API Contract

### POST /api/v1/telemetry
```json
// Request (no tenant_id field)
{
    "device_id": "uuid",
    "datapoint_id": "uuid",
    "event_time": "2026-09-02T11:00:00Z",
    "ingested_at": "2026-09-02T11:00:01Z",
    "value": 23.5,
    "data_type": "FLOAT",
    "unit": "degC",
    "quality": "GOOD",
    "metadata": {}
}

// Response
{
    "success": true,
    "data": {
        "id": "uuid",
        "device_id": "uuid",
        "datapoint_id": "uuid",
        "event_time": "...",
        "ingested_at": "...",
        "value": 23.5,
        "data_type": "FLOAT",
        "unit": "degC",
        "quality": "GOOD",
        "metadata": {}
    }
}
```

### GET /api/v1/telemetry/device/{device_id}
```json
// Response
{
    "total": 100,
    "device_id": "uuid",
    "start_time": "2026-09-01T00:00:00Z",
    "end_time": "2026-09-02T11:00:00Z",
    "points": [...]
}
```

---

## 9. Test Requirements

### Minimum Test Coverage
```
tests/telemetry/
├── __init__.py
├── test_ingestion.py
│   ├── test_save_telemetry
│   ├── test_batch_save
│   ├── test_timezone_required
│   └── test_utc_conversion
├── test_security.py
│   ├── test_cross_tenant_ingestion_blocked
│   └── test_cross_tenant_query_blocked
├── test_repository.py
│   └── test_repository_applies_tenant_filter
└── test_migration.py
    └── test_migration_import
```

### Quality Gates
- [ ] 228+ tests passing (baseline from Task 6)
- [ ] ruff check clean
- [ ] No protocol names in telemetry code
- [ ] No adapter imports in telemetry module

---

## 10. Acceptance Criteria

### Must Pass
1. ✅ Telemetry ingestion validates tenant ownership
2. ✅ Cross-tenant ingestion is rejected
3. ✅ Timestamps are UTC-aware
4. ✅ Batch operations are atomic (all-or-nothing)
5. ✅ Queries apply tenant filter automatically
6. ✅ No protocol coupling
7. ✅ No repository access in adapter layer

### Must Not
1. ❌ Modify services/adapter/
2. ❌ Add new dependencies
3. ❌ Implement any real protocol
4. ❌ Store secrets in plain text
5. ❌ Leak endpoint information in responses

---

**Next Step:** Await Task 7 Engineering Implementation
