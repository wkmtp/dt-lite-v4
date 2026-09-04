# DT-Lite V4.0 Phase 1 — Core Kernel Freeze Specification

**Document ID:** ARCH-FREEZE-001  
**Status:** FROZEN 🔒  
**Effective Date:** 2026-09-03  
**Architecture Authority:** Architecture Guardian (AI)  
**Classification:** Core Kernel Baseline

---

## 0. Freeze Status

### Architecture Status: APPROVED ✅

| Component | Status | Review Date |
|-----------|--------|-------------|
| Task 1: Database Foundation | ✅ FREEZE | 2026-09-03 |
| Task 1.5: Architecture Hardening | ✅ FREEZE | 2026-09-03 |
| Task 2: ORM + Repository Layer | ✅ FREEZE | 2026-09-03 |
| Task 2.1: Repository Hardening | ✅ FREEZE | 2026-09-03 |
| Task 3: Permission Service | ✅ FREEZE | 2026-09-03 |
| Task 4: Security Architecture | ✅ FREEZE | 2026-09-03 |
| Task 6: Adapter Contract Boundary | ✅ FREEZE | 2026-09-03 |
| Task 7: Telemetry Foundation | ✅ FREEZE | 2026-09-03 |
| Task 8: Twin Runtime | ✅ FREEZE | 2026-09-03 |
| Task 9: Twin Persistence | ✅ FREEZE | 2026-09-03 |
| Task 10: Twin Graph & Semantic Query | ✅ FREEZE | 2026-09-03 |
| Task 10.1: Architecture Hardening | ✅ FREEZE | 2026-09-03 |

### Freeze Mode: ENABLED 🔒

This document represents **THE FINAL ARCHITECTURE BASELINE** for all future DT-Lite development. Any modification requires:
1. Architecture Review
2. ADR Approval
3. Regression Validation

---

## 1. Document Objective

This specification defines:
1. **What is frozen** — immutable architectural boundaries
2. **What future developers must not modify** — protected layers and invariants
3. **Allowed extension points** — Phase 2 integration paths
4. **Phase 2 integration rules** — contract boundaries
5. **Architecture invariants** — mandatory enforcement rules
6. **Security guarantees** — tenant isolation model
7. **Dependency boundaries** — allowed cross-module imports

---

## 2. Executive Architecture Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DT-Lite V4.0 Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Identity   │     │  Authentication │   │ Authorization │    │
│  │   Layer      │     │   (JWT)         │   │   (RBAC)      │    │
│  └──────┬───────┘     └──────────────┘     └──────────────┘    │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              Tenant Security Context                      │     │
│  │         (TenantContext middleware)                         │     │
│  └──────────────────────────────────────────────────────────┘     │
│         │                                                          │
│         ├─────────────────────────────────────────────────────────┤
│         │                                                         │
│         ▼                                                         ▼
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ Adapter      │     │ Telemetry    │     │ Twin         │    │
│  │ Contract     │     │ Contract     │     │ Runtime      │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │               │                │                       │
│         │               │                │                       │
│         ▼               ▼                ▼                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Twin Persistence Layer                        │    │
│  │        (TwinEntity, TwinDefinition, TwinBinding)           │    │
│  └──────────────────────────────────────────────────────────┘    │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Twin Semantic Graph Layer                     │    │
│  │        (TwinRelationship, TwinQueryEngine)                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Data Flow

```
Request Flow:
  HTTP → Gateway → Auth Middleware → TenantContext → RBAC Check → Service → Repository

Physical Data Flow:
  Device → Adapter → NormalizedTelemetry → TelemetryService → Repository → DB

Semantic Data Flow:
  TwinEntity ←→ TwinRelationship ←→ TwinQueryEngine (Graph Traversal)

Runtime Data Flow:
  TelemetryService → TwinStateManager → TwinEntityRegistry (In-Memory)
```

### What Phase 1 Provides

**DT-Lite V4.0 Phase 1 = Industry-independent Digital Twin Kernel**

The kernel provides:
- Multi-tenant identity management
- JWT-based authentication and RBAC authorization
- Protocol-agnostic adapter contract
- Normalized telemetry ingestion pipeline
- Digital twin entity lifecycle management
- Semantic relationship graph storage and traversal

### What Phase 1 Does NOT Provide

Phase 1 does NOT implement:
- ❌ Building Management System (BMS) logic
- ❌ Manufacturing Execution System (MES)
- ❌ Full IoT Platform features (device provisioning, fleet management)
- ❌ BIM Platform integration
- ❌ Industry-specific templates (HVAC, lighting, access control)
- ❌ Protocol adapters (BACnet, Modbus, OPC-UA implementations)
- ❌ 3D visualization engine
- ❌ AI/ML agent framework

---

## 3. Frozen Module Definition

### 3.1 Identity Layer

**Location:** `services/identity/**`

**Responsibilities:**
- Tenant lifecycle management (create, read, update, deactivate)
- User account management (registration, authentication, password policy)
- Role-based access control (role creation, permission assignment, user-role mapping)
- Permission definitions and evaluation

**Key Models:**
```
Tenant          → organizations.id
User            → users.id (tenant-scoped)
Role            → roles.id (tenant-scoped)
Permission      → permissions.id (system-wide)
UserRole        → user_roles (junction)
RolePermission  → role_permissions (junction)
```

**Frozen Constraints:**
- ❌ NO industry-specific user attributes
- ❌ NO custom authentication providers
- ❌ NO hardcoded role names (use code-based RBAC)
- ❌ NO direct database queries outside repository layer

**Protected Files:**
- `models/models.py` — schema definition
- `repositories/` — data access boundary
- `services/auth_service.py` — JWT handling
- `dependencies.py` — security middleware

---

### 3.2 Core Repository Layer

**Location:** `services/core/**`

**Responsibilities:**
- SQLAlchemy 2.x Typed ORM base classes (`Base`, `SoftDeleteMixin`, `TimestampMixin`)
- Generic repository contract (`BaseRepository`, `TenantAwareRepository`)
- Unit of work pattern (`UnitOfWork`)
- Core domain models (Entity, Asset, PropertyDefinition, PropertyValue, Relationship)

**Key Models:**
```
Entity            → entities.id (digital twin definition)
Asset             → assets.id (physical/logical asset)
PropertyDefinition → property_definitions.id (schema definition)
PropertyValue     → property_values (entity+property composite PK)
Relationship      → relationships.id (semantic connections)
```

**Frozen Constraints:**
- ❌ NO protocol-specific fields
- ❌ NO direct SQL execution in service layer
- ❌ NO bypassing `TenantAwareRepository` for tenant-scoped queries
- ❌ NO hardcoding industry entity types

**Protected Patterns:**
```python
# Required: Use TenantAwareRepository
repo = EntityRepository(session)
entity = await repo.get_by_id_for_tenant(entity_id, tenant_id)

# Forbidden: Direct session.execute with tenant query
stmt = select(Entity).where(Entity.id == entity_id)  # Missing tenant filter!
```

---

### 3.3 Adapter Contract Layer

**Location:** `services/adapter/**`

**Responsibilities:**
- Protocol adapter interface definition (`ProtocolAdapter` abstract class)
- Runtime adapter registry (`AdapterRegistry`)
- Health monitoring and lifecycle management
- Endpoint abstraction (no credential exposure)

**Key Classes:**
```python
class ProtocolAdapter(Protocol):
    """Abstract base for all protocol adapters."""
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def read(self, address: str) -> Any: ...
    async def write(self, address: str, value: Any) -> None: ...
    async def poll(self) -> list[NormalizedTelemetry]: ...

class AdapterInstance:
    """Runtime tracking for registered adapters."""
```

**Frozen Constraints:**
- ❌ NO protocol-specific implementations (BACnet, Modbus, OPC-UA) — these are Phase 2
- ❌ NO credentials stored in runtime models
- ❌ NO direct database coupling

**Phase 2 Extension:**
- Implement BACnet adapter → `plugins/iot/bacnet.py`
- Implement Modbus adapter → `plugins/iot/modbus.py`
- Implement OPC-UA adapter → `plugins/iot/opcua.py`

---

### 3.4 Telemetry Layer

**Location:** `services/telemetry/**`

**Responsibilities:**
- Normalized telemetry ingestion pipeline
- Time-series data storage (`TelemetryPoint` model)
- Query engine for historical data retrieval
- Data quality validation

**Key Model:**
```python
class TelemetryPoint(Base):
    """Time-series telemetry data point."""
    id: UUID
    tenant_id: UUID           # NOT NULL
    device_id: UUID           # FK → devices.id
    datapoint_id: UUID        # FK → data_points.id
    event_time: datetime      # Device measurement timestamp
    ingested_at: datetime     # System receive timestamp
    value: JSONB              # Measurement value
    data_type: str            # BOOLEAN/INTEGER/FLOAT/STRING/JSON
    unit: Optional[str]       # Physical unit
    quality: str              # GOOD/BAD/UNCERTAIN/UNKNOWN
    metadata: JSONB           # Additional context
```

**Frozen Constraints:**
- ❌ NO business semantics (no "temperature", "pressure" — use generic `value`)
- ❌ NO telemetry stored in twin graph
- ❌ NO bypassing normalization layer
- ❌ NO direct device-to-database coupling

**Key Contracts:**
- `NormalizedTelemetry` — standardized data format from adapters
- `TelemetryPointCreate` — Pydantic schema for ingestion requests

---

### 3.5 Twin Runtime Layer

**Location:** `services/twin/**`

**Responsibilities:**
- In-memory digital twin state management
- Runtime entity registry (`TwinEntityRegistry`)
- State synchronization from telemetry
- Visualization-ready state representation

**Key Model:**
```python
@dataclass
class TwinEntity:
    """In-memory runtime representation of a digital twin."""
    id: UUID
    tenant_id: UUID
    name: str
    entity_type: str
    template: dict
    device_id: Optional[UUID]
    runtime_state: dict       # Current state (temperature, status, etc.)
    created_at: datetime
    updated_at: datetime
```

**Frozen Constraints:**
- ❌ NO database as runtime source (registry is in-memory only)
- ❌ NO persistence of runtime state (use separate TwinStateManager)
- ❌ NO protocol-specific state fields
- ❌ NO telemetry values stored directly

**Runtime vs Persistence Separation:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Twin Runtime (Memory)                     │
│  TwinEntityRegistry                                         │
│    ├─ TwinEntity (id, name, type, runtime_state)            │
│    └─ Updated by: TwinStateManager                         │
└─────────────────────────────────────────────────────────────┘
                          ↕ Sync
┌─────────────────────────────────────────────────────────────┐
│                   Twin Persistence (Database)                │
│  entities table                                             │
│    ├─ TwinEntity (definition, metadata)                     │
│    └─ TwinDefinition (schema, templates)                    │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.6 Twin Persistence Layer

**Location:** `services/twin/**` (models and repositories)

**Responsibilities:**
- Twin entity lifecycle management (create, update, delete)
- Twin definition storage (type schemas, templates)
- Twin binding management (link to physical devices)

**Key Models:**
```python
class PersistentTwinEntity(Base, SoftDeleteMixin):
    """Database model for twin entity definition."""
    id: UUID
    tenant_id: UUID           # NOT NULL
    entity_type: str          # e.g., "sensor", "actuator", "area"
    name: str
    description: Optional[str]
    extra_data: JSONB
```

**Frozen Constraints:**
- ❌ NO real-time state storage (runtime state belongs in memory)
- ❌ NO protocol-specific fields
- ❌ NO direct coupling to adapter layer

---

### 3.7 Twin Graph Layer

**Location:** `services/twin_graph/**`

**Responsibilities:**
- Semantic relationship storage (`TwinRelationship`)
- Graph traversal and path finding
- Neighbor discovery
- Relationship validation

**Key Model:**
```python
class TwinRelationship(Base, SoftDeleteMixin):
    """Semantic relationship between two twin entities."""
    id: UUID
    tenant_id: UUID           # NOT NULL
    source_twin_id: UUID      # FK → twin_entities.id (CASCADE)
    target_twin_id: UUID      # FK → twin_entities.id (CASCADE)
    relationship_type: str    # e.g., "contains", "located_in", "connected_to"
    metadata: JSONB
```

**Frozen Constraints:**
- ❌ NO telemetry values stored in relationships
- ❌ NO hardcoded relationship types (e.g., `if relationship_type == "floor"`)
- ❌ NO external graph database dependencies (Neo4j, NetworkX)
- ❌ NO self-referencing relationships (CHECK constraint enforced)

**Allowed Relationship Types:**
- `contains` — hierarchical containment
- `located_in` — spatial placement
- `connected_to` — physical/electrical connection
- `controls` — control relationship
- `monitors` — observation relationship
- `depends_on` — dependency relationship

---

## 4. Architecture Invariants

### Invariant 1: Tenant Isolation

**ALL tenant information MUST originate from:**

```
JWT Token
    ↓
get_current_user()      → Extracts user_id
    ↓
get_current_tenant()    → Sets TenantContext
    ↓
require_permission()    → Validates access
    ↓
Service Layer           → Uses tenant_id from context
```

**FORBIDDEN sources:**
```python
# ❌ FORBIDDEN: From HTTP header
tenant_id = request.headers.get("x-tenant-id")

# ❌ FORBIDDEN: From request body
body = RelationshipCreateRequest(...)
tenant_id = body.tenant_id  # Must come from context!

# ❌ FORBIDDEN: From URL parameter
@app.get("/tenants/{tenant_id}/relationships")
async def get_relationships(tenant_id: UUID):  # NEVER do this
```

**ENFORCED sources:**
```python
# ✅ CORRECT: From JWT context
async def get_neighbors(
    twin_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),  # ← REQUIRED
):
    pass
```

---

### Invariant 2: Repository Boundary

**Service Layer:**
```python
# ✅ ALLOWED: Use repository methods
rel = await self._repo.get_by_ids(source_id, target_id, tenant_id)

# ❌ FORBIDDEN: Direct database queries
stmt = select(TwinRelationship).where(...)
result = await self.session.execute(stmt)  # NEVER do this in service
```

**Repository Layer:**
```python
# ✅ ALLOWED: flush, refresh
await self.session.flush()
await self.session.refresh(obj)

# ❌ FORBIDDEN: commit, rollback
self.session.commit()   # NEVER — transaction control belongs to application layer
self.session.rollback() # NEVER — handled by framework
```

---

### Invariant 3: Runtime Separation

| Layer | Storage | Purpose |
|-------|---------|---------|
| **Runtime State** | In-Memory (TwinEntityRegistry) | Real-time visualization, quick lookup |
| **Persistence** | PostgreSQL (entities table) | Entity definitions, metadata, lifecycle |
| **Semantic Graph** | PostgreSQL (twin_relationships) | Relationships, topology, queries |
| **Telemetry** | PostgreSQL (telemetry_points) | Time-series data, historical analysis |

**NEVER mix these concerns:**
```python
# ❌ FORBIDDEN: Storing runtime state in database
class TwinEntity(Base):
    temperature: float  # This is runtime state!
    
# ✅ CORRECT: Runtime state in memory, definition in database
@dataclass
class TwinEntity:
    runtime_state: dict  # Memory only

class PersistentTwinEntity(Base):
    entity_type: str     # Database only
```

---

### Invariant 4: Industry Neutral Core

**The core kernel MUST NOT depend on:**
- ❌ BACnet (protocol library)
- ❌ MQTT (message broker)
- ❌ OPC-UA (industrial protocol)
- ❌ Modbus (industrial protocol)
- ❌ PLC (hardware abstraction)
- ❌ BIM (building information modeling)
- ❌ SCADA (supervisory control)
- ❌ Neo4j (graph database)
- ❌ NetworkX (graph library)

**Allowed dependencies:**
- ✅ `services.core.*` — Base models, repositories
- ✅ `services.identity.*` — User, tenant, role, permission
- ✅ `services.auth.*` — JWT handling, security middleware
- ✅ `services.twin.*` — Twin runtime and persistence
- ✅ `services.telemetry.*` — Telemetry ingestion and query

---

## 5. Data Model Freeze

### Core Domain Entities

#### Tenant

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `name` | String(128) | NOT NULL |
| `code` | String(64) | UNIQUE, indexed |
| `status` | String(32) | DEFAULT 'active' |
| `extra_data` | JSONB | NOT NULL, default `{}` |
| `deleted_at` | DateTime | Nullable (soft delete) |

**Purpose:** Represents an organization in the multi-tenant system.  
**Ownership:** Identity service (`services/identity/`)  
**Lifecycle:** Created → Active → Deactivated (soft delete)  
**Forbidden Fields:** `industry_type`, `subscription_tier`, `api_key`

---

#### User

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `username` | String(128) | NOT NULL, unique per tenant |
| `email` | String(255) | Nullable |
| `password_hash` | String(255) | NOT NULL, bcrypt hashed |
| `status` | String(32) | DEFAULT 'active' |
| `extra_data` | JSONB | NOT NULL |
| `deleted_at` | DateTime | Nullable |

**Purpose:** User account within a tenant.  
**Ownership:** Identity service (`services/identity/`)  
**Lifecycle:** Registered → Active → Suspended → Deleted  
**Forbidden Fields:** `department`, `role_name`, `protocol_access`

---

#### Role

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `name` | String(128) | NOT NULL |
| `code` | String(64) | UNIQUE per tenant |
| `extra_data` | JSONB | NOT NULL |
| `deleted_at` | DateTime | Nullable |

**Purpose:** RBAC role within a tenant.  
**Ownership:** Identity service (`services/identity/`)  
**Lifecycle:** Created → Assigned → Removed  
**Forbidden Fields:** `industry_role`, `hierarchy_level`

---

#### Permission

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `code` | String(128) | UNIQUE, system-wide |
| `description` | String(512) | Nullable |
| `extra_data` | JSONB | NOT NULL |
| `deleted_at` | DateTime | Nullable |

**Purpose:** System-wide permission definition (not tenant-scoped).  
**Ownership:** Identity service (`services/identity/`)  
**Lifecycle:** Defined → Assigned to Roles → Revoked  
**Forbidden Fields:** `resource_type`, `action_type` (use code-based naming)

---

#### NormalizedTelemetry

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `device_id` | UUID | FK → devices.id, NOT NULL |
| `datapoint_id` | UUID | FK → data_points.id, NOT NULL |
| `event_time` | DateTime | NOT NULL, indexed |
| `ingested_at` | DateTime | NOT NULL, default now() |
| `value` | JSONB | NOT NULL |
| `data_type` | String(32) | ENUM: BOOLEAN/INTEGER/FLOAT/STRING/JSON |
| `unit` | String(64) | Nullable |
| `quality` | String(32) | DEFAULT 'GOOD' |
| `metadata` | JSONB | NOT NULL |

**Purpose:** Stores normalized telemetry data points.  
**Ownership:** Telemetry service (`services/telemetry/`)  
**Lifecycle:** Appended only (no updates, no deletes)  
**Forbidden Fields:** `raw_value`, `protocol_address`, `source_device_type`

---

#### TwinEntity (Persistent)

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `entity_type` | String(128) | NOT NULL, indexed |
| `name` | String(255) | NOT NULL |
| `description` | String(512) | Nullable |
| `status` | String(32) | DEFAULT 'active' |
| `extra_data` | JSONB | NOT NULL |
| `deleted_at` | DateTime | Nullable |

**Purpose:** Defines a digital twin entity (schema/metadata only).  
**Ownership:** Twin service (`services/twin/`)  
**Lifecycle:** Created → Active → Archived → Deleted  
**Forbidden Fields:** `runtime_state`, `temperature`, `last_reading`, `protocol_address`

---

#### TwinRelationship

| Attribute | Type | Constraint |
|-----------|------|------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK → tenants.id, NOT NULL |
| `source_twin_id` | UUID | FK → twin_entities.id, CASCADE |
| `target_twin_id` | UUID | FK → twin_entities.id, CASCADE |
| `relationship_type` | String(64) | NOT NULL, pattern `^[a-zA-Z_][a-zA-Z0-9_]*$` |
| `metadata` | JSONB | NOT NULL, default `{}` |
| `created_at` | DateTime | NOT NULL |
| `updated_at` | DateTime | NOT NULL |
| `deleted_at` | DateTime | Nullable (soft delete) |

**Purpose:** Stores semantic relationships between twin entities.  
**Ownership:** Twin Graph service (`services/twin_graph/`)  
**Lifecycle:** Created → Active → Deleted (soft)  
**Constraints:** CHECK(`source_twin_id != target_twin_id`)

---

## 6. Security Model Freeze

### JWT Design

**Token Payload (Claims):**
```json
{
  "sub": "user-uuid",      // Required: User identifier
  "iat": 1234567890,       // Required: Issued at timestamp
  "exp": 1234567890        // Required: Expiration timestamp
}
```

**FORBIDDEN Claims:**
```json
{
  "roles": ["admin"],      // ❌ NEVER store roles in JWT
  "permissions": [...],    // ❌ NEVER store permissions in JWT
  "tenant_id": "xxx"       // ❌ NEVER store tenant_id in JWT (derive from sub)
}
```

**Rationale:** JWT should be minimal and stateless. Role/permission evaluation happens server-side via repository lookup.

---

### RBAC Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Login Request → AuthService.login()                        │
│       ↓                                                      │
│  Verify credentials (bcrypt)                                │
│       ↓                                                      │
│  Create JWT {sub, iat, exp}                                 │
│       ↓                                                      │
│  Return token to client                                     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    Authorization Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  API Request → get_current_user(token)                      │
│       ↓                                                      │
│  Decode JWT → Extract sub (user_id)                         │
│       ↓                                                      │
│  UserRepository.get_by_id(user_id)                          │
│       ↓                                                      │
│  Set TenantContext                                          │
│       ↓                                                      │
│  require_permission("resource:action")                      │
│       ↓                                                      │
│  PermissionService.check_permission(user_id, code, tenant)  │
│       ↓                                                      │
│  Allow / Deny                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Tenant Isolation Enforcement

| Level | Mechanism | Example |
|-------|-----------|---------|
| **API Layer** | `Depends(get_current_tenant)` | All routes require tenant from JWT |
| **Service Layer** | Pass `tenant_id` as explicit parameter | `create_relation(..., tenant_id: UUID)` |
| **Repository Layer** | `TenantAwareRepository._get_tenant_filter()` | All SELECT queries include `WHERE tenant_id = ?` |
| **Database Layer** | Row-level security (future) | Not yet implemented |

**Critical Rule:** Tenant ID must NEVER appear in request bodies or URL parameters.

---

## 7. Runtime Data Flow Freeze

### Physical Data Flow

```
┌─────────┐    ┌──────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Device  │───▶│ Adapter  │───▶│ Normalized       │───▶│ Telemetry       │───▶│ PostgreSQL   │
│         │    │          │    │ Telemetry        │    │ Service         │    │              │
└─────────┘    └──────────┘    └──────────────────┘    └─────────────────┘    └──────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │ TwinStateManager │
                                              │ (In-Memory)     │
                                              └─────────────────┘
```

### Semantic Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ TwinEntity      │────▶│ TwinRelationship │────▶│ TwinQueryEngine │
│ (Definition)    │     │ (Graph Edge)     │     │ (BFS/Path Find) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │ PostgreSQL   │         │ PostgreSQL   │         │ In-Memory    │
  │ entities     │         │ relationships│         │ (BFS cache)  │
  └──────────────┘         └──────────────┘         └──────────────┘
```

---

## 8. Extension Rules

### Allowed Phase 2 Extensions

| Extension | Location | Integration Point |
|-----------|----------|-------------------|
| Building Template | `plugins/industry/building/` | Schema templates for building domain |
| BACnet Adapter | `plugins/iot/bacnet.py` | Implement `ProtocolAdapter` |
| Modbus Adapter | `plugins/iot/modbus.py` | Implement `ProtocolAdapter` |
| OPC-UA Adapter | `plugins/iot/opcua.py` | Implement `ProtocolAdapter` |
| Device Discovery | `services/iot/services/discovery_service.py` | Extend IOT service |
| BIM Integration | `plugins/industry/bim/` | Import BIM models as TwinDefinitions |
| 3D Scene | `apps/web/src/components/scene3d/` | Frontend only, no backend changes |
| AI Agent | `services/ai/` | New service, uses Twin Graph API |

### Forbidden Modifications

```python
# ❌ FORBIDDEN: Adding protocol fields to TwinEntity
class TwinEntity(Base):
    bacnet_address: str      # NEVER
    plc_register: int        # NEVER
    mqtt_topic: str          # NEVER

# ✅ CORRECT: Create adapter plugin
# plugins/iot/bacnet.py implements ProtocolAdapter
```

---

## 9. Phase 2 Integration Contract

### Required Integration Points

Future systems MUST integrate through:

1. **Adapter Contract** — All protocol adapters implement `ProtocolAdapter`
2. **Telemetry Contract** — All data flows through `NormalizedTelemetry`
3. **Twin Runtime API** — Access runtime state via `TwinEntityRegistry`
4. **Twin Graph API** — Query relationships via `TwinQueryEngine`

### Forbidden Integration Patterns

```python
# ❌ FORBIDDEN: Direct database coupling
from services.database import AsyncSessionLocal
session = await AsyncSessionLocal()
await session.execute(select(TelemetryPoint))

# ✅ CORRECT: Use service layer
from services.telemetry.services import TelemetryService
service = TelemetryService(session)
points = await service.query_device_telemetry(device_id, start_time, end_time)
```

---

## 10. Testing Baseline Freeze

### Current Verified Baseline

| Metric | Value |
|--------|-------|
| Total Tests Passed | **489** |
| Skipped Tests | 12 |
| New Failures | **0** |
| Ruff Checks | **PASS** |
| Architecture Scan | **PASS** |

### Frozen Quality Gate

All future Pull Requests MUST maintain:

```
pytest -q                          → 0 failures
ruff check services/ tests/        → Clean
architecture_scan.py               → No new violations
```

### Test Coverage by Module

| Module | Test Count | Status |
|--------|------------|--------|
| Identity | ~80 | ✅ PASS |
| Core | ~100 | ✅ PASS |
| Auth | ~40 | ✅ PASS |
| Adapter | ~20 | ✅ PASS |
| Telemetry | ~44 | ✅ PASS |
| Twin | ~52 | ✅ PASS |
| Twin Graph | ~69 | ✅ PASS |
| Gateway | ~30 | ✅ PASS |

---

## 11. Architecture Decision Records

### ADR-001: Unified Tenant Security Model

**Status:** Accepted  
**Date:** 2026-09-03

**Decision:** All tenant information must originate from JWT context, never from request payloads.

**Context:** Multi-tenant SaaS applications require strict tenant isolation to prevent data leaks.

**Consequences:**
- ✅ Eliminates tenant impersonation attacks
- ✅ Centralizes security logic in middleware
- ⚠️ Requires all API consumers to pass valid JWT

---

### ADR-002: Repository Boundary

**Status:** Accepted  
**Date:** 2026-09-03

**Decision:** Service layer must never execute direct database queries; all data access must go through repository classes.

**Context:** Direct queries bypass tenant filtering and security checks.

**Consequences:**
- ✅ Ensures consistent tenant isolation
- ✅ Enables repository mocking for unit tests
- ⚠️ Adds indirection layer (acceptable trade-off)

---

### ADR-003: Runtime / Persistence Separation

**Status:** Accepted  
**Date:** 2026-09-03

**Decision:** Digital twin runtime state lives in-memory; persistent state lives in database. These are separate concerns.

**Context:** Mixing runtime and persistence causes stale data issues and complicates scaling.

**Consequences:**
- ✅ Fast runtime lookups (memory)
- ✅ Durable entity definitions (database)
- ⚠️ Requires synchronization mechanism (TwinStateManager)

---

### ADR-004: Industry Neutral Twin Kernel

**Status:** Accepted  
**Date:** 2026-09-03

**Decision:** Core kernel must not depend on any industry-specific protocols or libraries.

**Context:** Premature industry coupling prevents reusability across domains.

**Consequences:**
- ✅ Kernel usable for any industry
- ✅ Plugins can add protocol support
- ⚠️ Phase 2 must implement adapters separately

---

### ADR-005: Graph Semantic Layer

**Status:** Accepted  
**Date:** 2026-09-03

**Decision:** Use PostgreSQL for graph storage instead of external graph databases.

**Context:** External graph DBs add operational complexity without sufficient benefit for current scale.

**Consequences:**
- ✅ Single database ecosystem
- ✅ Transactional consistency
- ⚠️ Complex graph queries may be slower than native graph DB (acceptable for Phase 1-3)

---

## 12. Forbidden Future Changes

### Explicit Blacklist

The following modifications are **STRICTLY FORBIDDEN** without Architecture Review and ADR approval:

| # | Forbidden Change | Reason |
|---|------------------|--------|
| 1 | Add protocol fields to `TwinEntity` | Violates industry neutrality |
| 2 | Store telemetry inside `TwinRelationship` | Mixes concerns |
| 3 | Bypass repository layer | Breaks tenant isolation |
| 4 | Remove `TenantContext` middleware | Security vulnerability |
| 5 | Introduce industry dependencies into core | Violates ADR-004 |
| 6 | Replace PostgreSQL without ADR | Data migration risk |
| 7 | Introduce Neo4j/NetworkX without ADR | Violates ADR-005 |
| 8 | Add `commit()` to repository layer | Breaks transaction boundaries |
| 9 | Accept `tenant_id` from request body | Security vulnerability |
| 10 | Hardcode relationship types in service | Violates config-first principle |

---

## 13. Final Freeze Declaration

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║            DT-Lite V4.0 Phase 1 Core Kernel                      ║
║                                                                  ║
║                    STATUS: FROZEN 🔒                             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

**This architecture baseline is approved for:**
- Phase 2 Industry Enablement Development
- Plugin development (adapters, templates, agents)
- Integration testing and validation

**Any modification requires:**
1. Architecture Review by Architecture Guardian
2. ADR Approval (new or amended)
3. Regression Validation (all 489 tests must pass)
4. Security Audit (for authentication/authorization changes)

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-03  
**Next Review:** Upon Phase 2 completion  
**Authority:** DT-Lite Architecture Committee

---

*END OF SPECIFICATION*
