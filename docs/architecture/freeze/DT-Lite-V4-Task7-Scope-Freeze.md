# DT-Lite V4.0 Task 7 Scope Freeze Document
## Telemetry Ingestion & Persistence Layer

**Freeze Date:** 2026-09-02  
**Reviewer:** Architecture Guardian Agent  
**Effective Immediately Upon Approval**

---

## 1. Executive Summary

This document defines the immutable boundaries for Task 7 implementation. All modifications must adhere to this scope. Any deviation requires Architecture Exception submission.

---

## 2. Current Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1 Task Boundary                                               │
│                                                                     │
│  [Task 6] Adapter Runtime (FROZEN)                                 │
│      ↓ NormalizedTelemetry contract                                 │
│  [Task 7] Telemetry Ingestion & Persistence (THIS TASK)             │
│      ↓                                                              │
│  [Future] Telemetry Analytics / Streaming                           │
│                                                                     │
│  [Out of Scope]                                                     │
│    - Protocol implementations                                      │
│    - AI/Analytics                                                    │
│    - Infrastructure services                                       │
│    - Domain model creation                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Dependency Direction

### Allowed Imports (Inbound)
```python
# From Frozen Task 6 Contracts
from services.iota.contracts import NormalizedTelemetry
from services.iota.repositories.device_repository import DeviceRepository
from services.iota.repositories.data_point_repository import DataPointRepository
from services.iota.repositories.connection_repository import ConnectionRepository

# From Core Framework
from services.core.repositories.base import TenantAwareRepository
from services.tenant_context import get_tenant_id
```

### Forbidden Imports (Outbound)
```python
# NO protocol-specific imports
from services.adapter.*  # ❌ FORBIDDEN
import bacnet             # ❌ FORBIDDEN
import modbus             # ❌ FORBIDDEN
import opcua              # ❌ FORBIDDEN
import mqtt               # ❌ FORBIDDEN

# NO infrastructure dependencies
import kafka               # ❌ FORBIDDEN
import redis               # ❌ FORBIDDEN
import rabbitmq            # ❌ FORBIDDEN
import celery              # ❌ FORBIDDEN

# NO AI dependencies
from services.ai.*         # ❌ FORBIDDEN
```

---

## 4. Security Boundary

### 4.1 Tenant Isolation Requirements
```
MANDATORY:
  tenant_id ← Depends(get_current_tenant)  # JWT context ONLY
  tenant_id ∉ request.body                  # Never accept from client

RECOMMENDED:
  All queries MUST include: WHERE tenant_id = :tenant_id
```

### 4.2 Permission Matrix
| Operation | Permission | Enforcement |
|-----------|------------|-------------|
| Ingest single | `telemetry:create` | Route dependency |
| Ingest batch | `telemetry:create` | Route dependency |
| Query by device | `telemetry:read` | Route dependency |
| Query by datapoint | `telemetry:read` | Route dependency |
| Query range | `telemetry:read` | Route dependency |

### 4.3 Data Flow Validation
```
✓ POST /telemetry → validate(device_tenant == current_tenant)
✓ POST /telemetry → validate(datapoint_tenant == current_tenant)
✗ Cross-tenant write → REJECTED
✗ Missing ownership → ERROR 403/404
```

---

## 5. Database Alignment

### 5.1 Model-Column Mapping
| ORM Attribute | DB Column | Type | Constraints |
|---------------|-----------|------|-------------|
| `id` | `id` | UUID | PRIMARY KEY |
| `tenant_id` | `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `device_id` | `device_id` | UUID | FK → devices.id, CASCADE |
| `datapoint_id` | `datapoint_id` | UUID | FK → data_points.id, CASCADE |
| `event_time` | `event_time` | TIMESTAMPTZ | NOT NULL |
| `ingested_at` | `ingested_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `value` | `value` | JSONB | NOT NULL |
| `data_type` | `data_type` | VARCHAR(32) | NOT NULL |
| `unit` | `unit` | VARCHAR(64) | NULLABLE |
| `quality` | `quality` | VARCHAR(32) | NOT NULL, DEFAULT 'GOOD' |
| `meta_data` | `metadata` | JSONB | NOT NULL, DEFAULT '{}' |

### 5.2 Index Strategy
```sql
-- Primary query patterns optimized:
CREATE INDEX ix_telemetry_tenant_device_time 
  ON telemetry_points (tenant_id, device_id, event_time);

CREATE INDEX ix_telemetry_datapoint_time 
  ON telemetry_points (datapoint_id, event_time);

CREATE INDEX ix_telemetry_tenant_time 
  ON telemetry_points (tenant_id, event_time);
```

---

## 6. Test Requirements

### 6.1 Minimum Coverage Matrix
| Category | Minimum Tests | Required Scenarios |
|----------|---------------|-------------------|
| Ingestion | 4 | single, batch, validation, timezone |
| Security | 3 | cross-tenant device, cross-tenant datapoint, tenant filter |
| Repository | 3 | save, batch_save, query_range |
| API | 2 | ingestion endpoint, query endpoint |
| Architecture | 2 | no adapter dependency, no protocol dependency |
| **TOTAL** | **14** | |

### 6.2 Forbidden Test Patterns
```python
# ❌ DO NOT test protocol adapters
async def test_bacnet_ingestion(): ...  # FORBIDDEN

# ❌ DO NOT test infrastructure directly  
async def test_kafka_producer(): ...  # FORBIDDEN

# ❌ DO NOT test domain auto-creation
async def test_device_creation(): ...  # FORBIDDEN
```

---

## 7. Allowed Modification Files

### 7.1 New Files (Creation Permitted)
```
services/telemetry/
├── __init__.py
├── models.py
├── repositories.py
├── services.py
├── query_service.py
├── schemas.py
├── routes.py
├── exceptions.py
├── main.py
├── pyproject.toml
└── README.md

tests/telemetry/
├── __init__.py
├── test_ingestion.py
├── test_security.py
├── test_query.py
├── test_api.py
└── test_architecture.py
```

### 7.2 Modified Files (Explicitly Approved)
| File | Modification | Purpose |
|------|--------------|---------|
| `services/gateway/main.py` | Add telemetry router | Register endpoints |
| `database/migrations/versions/phase6_telemetry.py` | Pre-existing | Table definition |

---

## 8. Forbidden Modification Files

### 8.1 Absolute Prohibitions
```
❌ services/adapter/**       — Frozen boundary, NEVER modify
❌ tests/adapter/**          — Frozen boundary, NEVER modify  
❌ services/iota/contracts.py — Immutable contract
❌ services/iota/models/**   — Frozen domain models
❌ services/core/**          — Core framework stability
```

### 8.2 Content Prohibitions
```
❌ No protocol names in code:
   bacnet, modbus, opcua, mqtt, plc

❌ No infrastructure in service layer:
   kafka, redis, rabbitmq, celery, flink, spark

❌ No AI/analytics:
   ai, analytics, prediction, reasoning, inference
```

---

## 9. Risk Assessment

| Risk ID | Description | Severity | Mitigation |
|---------|-------------|----------|------------|
| R-001 | Metadata attribute conflict | LOW | Workaround documented |
| R-002 | Cross-tenant data leakage | CRITICAL | Tenant filter enforced in all queries |
| R-003 | Protocol coupling drift | MEDIUM | Architecture tests enforce boundary |
| R-004 | Migration downgrade failure | LOW | Downgrade script verified |

---

## 10. Freeze Decision Matrix

| Gate | Criteria | Decision |
|------|----------|----------|
| Task 6 Boundary | Zero adapter modifications | ✅ PASS |
| Architecture Alignment | Follows platform-first pattern | ✅ PASS |
| Security Verification | Tenant isolation enforced | ✅ PASS |
| ORM/Migration | Database alignment confirmed | ✅ PASS |
| Test Coverage | ≥14 tests passing | ✅ PASS (44 tests) |
| Scope Compliance | No forbidden imports | ✅ PASS |

---

## 11. Effective Date & Sign-off

```
Freeze Status: ACTIVE
Effective: 2026-09-02
Approved By: Architecture Guardian Agent

Next Step:
  AWAITING Engineering Implementation Approval
```

---

## 12. Exception Process

Any deviation from this frozen scope requires:

1. **Architecture Exception Request** with:
   - Justification
   - Impact analysis
   - Risk assessment
   - Proposed mitigation

2. **Review by**: Phase Lead Architect

3. **Documentation**: All exceptions logged in `docs/architecture/exceptions/`

---

*DT-Lite V4.0 Architecture Governance Document*  
*Task 7 Scope Freeze — Effective Immediately Upon Approval*
