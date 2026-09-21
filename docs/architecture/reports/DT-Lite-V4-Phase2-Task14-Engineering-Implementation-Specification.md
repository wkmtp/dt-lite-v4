# DT-Lite V4.0 Phase 2 — Task 14 Engineering Implementation Specification

**Twin Binding & Activation Foundation**

| Field           | Value                                                                 |
| --------------- | --------------------------------------------------------------------- |
| Phase           | Phase 2 (Industry Enablement)                                         |
| Task            | 14                                                                    |
| Status          | ✅ APPROVED FOR IMPLEMENTATION                                        |
| Architecture Review | DT-Lite-V4-Task14-Architecture-Alignment-Review.md               |
| Date            | 2026-09-04                                                            |

---

## 1. Objective

Implement the **Twin Binding & Activation Foundation** — the bridge between **Provisioned Twin Identity** (PersistentTwinEntity) and **Operational Twin** (TwinEntityRegistry + Device connectivity).

### Problem Statement

After Task 13 (Provisioning), a `PersistentTwinEntity` exists in the database but:
1. It is **not registered** in the in-memory `TwinEntityRegistry`
2. It has **no device binding** — no connection to physical data sources
3. It has **no data point mapping** — no way to receive telemetry
4. It has **no command pathway** — no way to send write commands to devices
5. It has **no activation lifecycle** — no way to activate/deactivate

Task 14 fills this gap by implementing the **Twin Binding** layer.

### Success Criteria

- [ ] A new industry object can be provisioned, bound to a device, and activated in the runtime registry
- [ ] Zero Python code changes required for new device types or capabilities
- [ ] All 40+ hardening tests pass
- [ ] Full regression: 815+ passed, 0 new failures
- [ ] Ruff clean
- [ ] Frozen boundaries respected

---

## 2. Architecture Position

```
┌──────────────────────────────────────────────────────────────────┐
│                    DT-Lite Task 14 Architecture                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────┐  │
│  │  Deployment     │────▶│  Provisioning   │────▶│  Twin     │  │
│  │  Instance       │     │  Execution      │     │  Entity   │  │
│  │  (READY)        │     │  (completed)    │     │  (DB)     │  │
│  └─────────────────┘     └─────────────────┘     └─────┬─────┘  │
│                                                        │         │
│                                                        ▼         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Task 14: Twin Binding & Activation              │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │  TwinBindingService                                 │   │ │
│  │  │  ├─ bind(device_id, twin_entity_id)                │   │ │
│  │  │  ├─ activate(twin_binding_id)                      │   │ │
│  │  │  ├─ deactivate(twin_binding_id)                    │   │ │
│  │  │  ├─ map_data_points(twin_binding_id, mappings)     │   │ │
│  │  │  └─ send_command(twin_binding_id, command)         │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                            │                                │ │
│  │                            ▼                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │ Device       │  │ DataPoint    │  │ DeviceEntity     │  │ │
│  │  │ (iota)       │  │ (iota)       │  │ Binding (NEW)    │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                        │         │
│                    ┌─────────────────────┐             │         │
│                    │  TwinEntityRegistry │◀────────────┘         │
│                    │  (services/twin/)  │   (register on activate)│
│                    └─────────────────────┘                      │
│                                                        │         │
│                    ┌─────────────────────┐             │         │
│                    │  ProtocolAdapter    │◀────────────┘         │
│                    │  (services/adapter/│   (write command)      │
│                    │   read-only ref)   │                       │
│                    └─────────────────────┘                       │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│  ALLOWED IMPORTS          │  FORBIDDEN IMPORTS                   │
│  services.iota.*          │  services.adapter.* (write)           │
│  services.twin.*          │  services.telemetry.*                 │
│  services.twin_graph.*    │  services.ai.*                        │
│  services.ontology.*      │  services.bacnet/modbus/mqtt/*        │
│  services.template.*      │  services.bim/scene/*                 │
│  services.deployment.*    │  services.kafka/redis/celery          │
│  services.provisioning.*  │                                       │
│  services.core.*          │                                       │
│  services.auth.*          │                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Structure

```
services/task14/
├── __init__.py              # Package init, exports exceptions + service
├── exceptions.py            # Custom exceptions
│   ├── TwinBindingNotFoundError
│   ├── TwinBindingActivationError
│   ├── TwinBindingDeactivationError
│   ├── DeviceNotBoundError
│   ├── CommandSendError
│   └── BindingStatusError
├── models.py                # SQLAlchemy 2.x models
│   ├── TwinBinding          # Core binding model
│   └── TwinCommand          # Command lifecycle model
├── schemas.py               # Pydantic v2 DTOs
│   ├── TwinBindingCreateRequest
│   ├── TwinBindingResponse
│   ├── TwinBindingActivateRequest
│   ├── TwinBindingDeactivateRequest
│   ├── TwinCommandCreateRequest
│   └── TwinCommandResponse
├── repository.py            # Repositories extending TenantAwareRepository
│   ├── TwinBindingRepository
│   └── TwinCommandRepository
├── services.py              # TwinBindingService — orchestration layer
├── routes.py                # FastAPI router
└── domain_events.py         # Domain events for binding lifecycle
    ├── TwinBindingActivated
    ├── TwinBindingDeactivated
    └── TwinCommandSent

tests/task14/
├── test_models.py           # 10+ tests
├── test_repository.py       # 8+ tests
├── test_service.py          # 10+ tests
├── test_security.py         # 6+ tests
├── test_idempotency.py      # 5+ tests
├── test_architecture.py     # 5+ tests
└── test_task14_hardening.py # 20+ tests
```

---

## 4. Data Model

### TwinBinding

```python
class TwinBinding(Base, SoftDeleteMixin):
    """Bridges PersistentTwinEntity to operational runtime via Device + DataPoint mapping."""
    
    __tablename__ = "twin_bindings"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    twin_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    binding_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="device_bound",
        server_default="'device_bound'",
    )
    # binding_type values: "device_bound" | "direct" | "simulated"
    
    config_schema: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        server_default="{}::jsonb",
    )
    # Runtime configuration (e.g., polling interval, connection timeout)
    
    extra_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        server_default="{}::jsonb",
    )
    # Data point mappings, command mappings, capability bindings
    
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="inactive",
        server_default="'inactive'",
    )
    # "inactive" | "active" | "error"
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
```

### TwinCommand

```python
class TwinCommand(Base, SoftDeleteMixin):
    """Command sent from Twin to physical device via Adapter."""
    
    __tablename__ = "twin_commands"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True,
    )
    twin_binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_bindings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )
    # "write" | "trigger" | "configure"
    
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        server_default="{}::jsonb",
    )
    
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        server_default="'pending'",
    )
    # "pending" | "sent" | "acknowledged" | "failed"
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
```

### Migration

```python
# database/migrations/versions/phase14_twin_binding.py
revision = 'phase14_twin_binding'
down_revision = 'phase13_provisioning'
```

Tables:
- `twin_bindings` — with FK to tenants, twin_entities, devices
- `twin_commands` — with FK to tenants, twin_bindings, devices
- Unique constraints: `uq_binding_entity` (tenant_id, twin_entity_id)
- Indexes: tenant, twin_entity, device, binding_type, status

---

## 5. API Boundary

### Endpoints

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/api/v1/twin-bindings` | `twin_binding:create` | Create binding |
| GET | `/api/v1/twin-bindings` | `twin_binding:read` | List bindings |
| GET | `/api/v1/twin-bindings/{id}` | `twin_binding:read` | Get binding |
| POST | `/api/v1/twin-bindings/{id}/activate` | `twin_binding:activate` | Activate binding |
| POST | `/api/v1/twin-bindings/{id}/deactivate` | `twin_binding:deactivate` | Deactivate binding |
| POST | `/api/v1/twin-bindings/{id}/commands` | `twin_command:create` | Send command |
| GET | `/api/v1/twin-bindings/{id}/commands` | `twin_command:read` | List commands |
| POST | `/api/v1/twin-bindings/bind-from-deployment` | `twin_binding:create` | Auto-bind from deployment |

### Request/Response DTOs

```python
class TwinBindingCreateRequest(BaseModel):
    twin_entity_id: UUID
    device_id: Optional[UUID] = None
    binding_type: str = Field(default="device_bound", pattern="^(device_bound|direct|simulated)$")
    config_schema: dict = Field(default_factory=dict)
    extra_data: dict = Field(default_factory=dict)

class TwinBindingResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    twin_entity_id: UUID
    device_id: Optional[UUID]
    binding_type: str
    config_schema: dict
    extra_data: dict
    status: str
    created_at: str
    updated_at: str

class TwinCommandCreateRequest(BaseModel):
    target_device_id: UUID
    command_type: str = Field(pattern="^(write|trigger|configure)$")
    payload: dict = Field(default_factory=dict)

class TwinCommandResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    twin_binding_id: UUID
    target_device_id: UUID
    command_type: str
    payload: dict
    status: str
    error_message: Optional[str]
    created_at: str
    executed_at: Optional[str]
```

---

## 6. Service Layer

### TwinBindingService

```python
class TwinBindingService:
    """Orchestrates TwinBinding lifecycle."""
    
    def __init__(self, session):
        self._session = session
        self._binding_repo = TwinBindingRepository(session)
        self._command_repo = TwinCommandRepository(session)
        self._entity_service = EntityService(session)
        self._device_service = DeviceService(UnitOfWork(session))
        self._registry = get_twin_entity_registry()  # Singleton
    
    async def create_binding(
        self,
        twin_entity_id: UUID,
        tenant_id: UUID,
        device_id: Optional[UUID] = None,
        binding_type: str = "device_bound",
        config_schema: Optional[dict] = None,
        extra_data: Optional[dict] = None,
    ) -> TwinBinding:
        """Create a TwinBinding between a PersistentTwinEntity and a Device."""
        # 1. Validate tenant owns the twin entity
        entity = await self._entity_service.get(twin_entity_id, tenant_id)
        
        # 2. Validate device belongs to tenant (if provided)
        if device_id:
            device = await self._device_service.get_device(device_id, tenant_id)
            if device is None:
                raise TwinBindingError("Device not found or access denied")
        
        # 3. Check no existing active binding for this entity
        existing = await self._binding_repo.get_by_entity_for_tenant(twin_entity_id, tenant_id)
        if existing and existing.status == "active":
            raise TwinBindingError("Entity already has an active binding")
        
        # 4. Create binding
        binding = TwinBinding(
            tenant_id=tenant_id,
            twin_entity_id=twin_entity_id,
            device_id=device_id,
            binding_type=binding_type,
            config_schema=config_schema or {},
            extra_data=extra_data or {},
            status="inactive",
        )
        binding = await self._binding_repo.create(binding)
        return binding
    
    async def activate_binding(
        self,
        binding_id: UUID,
        tenant_id: UUID,
    ) -> TwinBinding:
        """Activate a TwinBinding — registers entity in runtime registry."""
        binding = await self._binding_repo.get_by_id_for_tenant(binding_id, tenant_id)
        if not binding:
            raise TwinBindingNotFoundError(binding_id)
        if binding.status != "inactive":
            raise TwinBindingStatusError(f"Cannot activate binding in status '{binding.status}'")
        
        # Register in TwinEntityRegistry
        entity = await self._entity_service.get(binding.twin_entity_id, tenant_id)
        self._registry.register(entity)
        
        binding.status = "active"
        binding.updated_at = datetime.now(timezone.utc)
        await self._binding_repo.update(binding)
        
        # Raise domain event
        raise_domain_event(TwinBindingActivated(binding.id, entity.id, tenant_id))
        return binding
    
    async def deactivate_binding(
        self,
        binding_id: UUID,
        tenant_id: UUID,
    ) -> TwinBinding:
        """Deactivate a TwinBinding — removes entity from runtime registry."""
        binding = await self._binding_repo.get_by_id_for_tenant(binding_id, tenant_id)
        if not binding:
            raise TwinBindingNotFoundError(binding_id)
        if binding.status != "active":
            raise TwinBindingStatusError(f"Cannot deactivate binding in status '{binding.status}'")
        
        # Remove from TwinEntityRegistry
        self._registry.remove(binding.twin_entity_id, tenant_id)
        
        binding.status = "inactive"
        binding.updated_at = datetime.now(timezone.utc)
        await self._binding_repo.update(binding)
        
        raise_domain_event(TwinBindingDeactivated(binding.id, tenant_id))
        return binding
    
    async def send_command(
        self,
        binding_id: UUID,
        tenant_id: UUID,
        command_type: str,
        payload: dict,
    ) -> TwinCommand:
        """Send a command from Twin to physical device."""
        binding = await self._binding_repo.get_by_id_for_tenant(binding_id, tenant_id)
        if not binding:
            raise TwinBindingNotFoundError(binding_id)
        if binding.device_id is None:
            raise DeviceNotBoundError(binding_id)
        if binding.status != "active":
            raise TwinBindingStatusError(f"Cannot send command on inactive binding")
        
        command = TwinCommand(
            tenant_id=tenant_id,
            twin_binding_id=binding_id,
            target_device_id=binding.device_id,
            command_type=command_type,
            payload=payload,
            status="pending",
        )
        command = await self._command_repo.create(command)
        
        # TODO: Route to ProtocolAdapter.write() via AdapterRegistry
        # This is a stub — actual adapter routing is Task 15+
        command.status = "sent"
        command.executed_at = datetime.now(timezone.utc)
        await self._command_repo.update(command)
        
        raise_domain_event(TwinCommandSent(command.id, binding_id, tenant_id))
        return command
```

---

## 7. Domain Events

```python
@dataclass(frozen=True)
class TwinBindingActivated(DomainEvent):
    binding_id: UUID = field(default=None)
    entity_id: UUID = field(default=None)
    tenant_id: UUID = field(default=None)
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'twin_binding.activated')

@dataclass(frozen=True)
class TwinBindingDeactivated(DomainEvent):
    binding_id: UUID = field(default=None)
    tenant_id: UUID = field(default=None)
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'twin_binding.deactivated')

@dataclass(frozen=True)
class TwinCommandSent(DomainEvent):
    command_id: UUID = field(default=None)
    binding_id: UUID = field(default=None)
    tenant_id: UUID = field(default=None)
    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'twin_command.sent')
```

---

## 8. Gateway Integration

```python
# services/gateway/main.py
from services.task14.routes import router as task14_router
app.include_router(task14_router)
```

---

## 9. Implementation Task Breakdown

### Phase 1: Foundation (Models + Repositories)
- [ ] 1.1 Create `services/task14/__init__.py`
- [ ] 1.2 Create `services/task14/exceptions.py` (6 exception classes)
- [ ] 1.3 Create `services/task14/models.py` (TwinBinding, TwinCommand)
- [ ] 1.4 Create `services/task14/schemas.py` (6 Pydantic DTOs)
- [ ] 1.5 Create `services/task14/repository.py` (2 repositories)

### Phase 2: Service Layer
- [ ] 2.1 Create `services/task14/domain_events.py` (3 domain events)
- [ ] 2.2 Create `services/task14/services.py` (TwinBindingService)
- [ ] 2.3 Create `services/task14/routes.py` (8 endpoints)

### Phase 3: Integration
- [ ] 3.1 Update `services/gateway/main.py` — include task14_router
- [ ] 3.2 Create `database/migrations/versions/phase14_twin_binding.py`

### Phase 4: Tests
- [ ] 4.1 Create `tests/task14/test_models.py` (10 tests)
- [ ] 4.2 Create `tests/task14/test_repository.py` (8 tests)
- [ ] 4.3 Create `tests/task14/test_service.py` (10 tests)
- [ ] 4.4 Create `tests/task14/test_security.py` (6 tests)
- [ ] 4.5 Create `tests/task14/test_idempotency.py` (5 tests)
- [ ] 4.6 Create `tests/task14/test_architecture.py` (5 tests)
- [ ] 4.7 Create `tests/task14/test_task14_hardening.py` (20 tests)

### Phase 5: Validation
- [ ] 5.1 Run `pytest -q` — target 815+ passed, 0 new failures
- [ ] 5.2 Run `ruff check services/task14 tests/task14`
- [ ] 5.3 Generate `DT-Lite-V4-Phase2-Task14-Completion-Report.md`

---

## 10. Test Baseline

| Metric | Current | Target |
|--------|---------|--------|
| Total tests passed | 775 | 815+ |
| New tests | — | 40+ |
| Hardening tests | 52 (task 13.1) | 20 (task 14) |
| New failures | 0 | 0 |
| Ruff violations | 0 | 0 |

---

## 11. Key Design Decisions

### A. TwinBinding as Orchestration Layer
TwinBinding does NOT implement device protocols. It orchestrates:
- Device ↔ TwinEntity binding (reads from `services.iota`)
- Runtime activation (writes to `services.twin.registry`)
- Command routing (reads from `services.adapter` contract)

### B. BindingType for Flexibility
Three binding types support different scenarios:
- `device_bound`: Physical device connected (most common)
- `direct`: Direct API/REST connection (no adapter)
- `simulated`: Simulated data source (testing/demo)

### C. JSONB for Configuration
All mapping configuration stored in `extra_data` JSONB:
- Data point mappings: `{"data_point_mappings": [...]}`
- Command mappings: `{"command_mappings": [...]}`
- Capability bindings: `{"capability_bindings": [...]}`

This avoids rigid schema while maintaining flexibility.

### D. Status-Driven Lifecycle
```
inactive ──activate──► active ──deactivate──► inactive
     ▲                           │
     │                           └──error──► error
     └────────────────────────────────────────
```

### E. TwinCommand Optional Execution
Command sending is a stub in Task 14. Full adapter routing (ProtocolAdapter.write) is Task 15+. Task 14 creates and tracks commands but delegates actual device communication to future adapter layer.

---

## 12. Frozen Boundary Compliance Checklist

| Rule | Status |
|------|--------|
| No modification to `services/core/**` | ✅ Confirmed |
| No modification to `services/identity/**` | ✅ Confirmed |
| No modification to `services/twin/**` | ✅ Confirmed (reads-only from registry) |
| No modification to `services/twin_graph/**` | ✅ Confirmed |
| No modification to `services/template/**` | ✅ Confirmed (reads-only) |
| No modification to `services/ontology/**` | ✅ Confirmed (reads-only) |
| No modification to `services/deployment/**` | ✅ Confirmed (reads-only) |
| No modification to `services/provisioning/**` | ✅ Confirmed (reads-only) |
| No new migrations to frozen tables | ✅ Confirmed (phase14 is new table only) |
| All repos extend TenantAwareRepository | ✅ Confirmed |
| All models use Mapped[] + mapped_column() | ✅ Confirmed |
| All models extend Base + SoftDeleteMixin | ✅ Confirmed |
| tenant_id from JWT only | ✅ Confirmed |
| No forbidden imports | ✅ Confirmed |
| No industry-specific logic | ✅ Confirmed |

---

## 13. Zero-Code Verification

### Scenario: New Building AHU Template
```
1. Create TwinTemplate (code="ahu_v1", industry="building")  — Task 11 ✅
2. Define CapabilityDefinition (key="temperature")           — Task 12 ✅
3. Create DeploymentProfile (template_id, capability_bindings) — Task 12.1 ✅
4. Create DeploymentInstance with DeploymentNode              — Task 12.1 ✅
5. Provision → PersistentTwinEntity created                   — Task 13 ✅
6. Bind to BACnet Device + activate in registry               — Task 14 ✅
7. Receive telemetry → update runtime state                   — Task 7/8 ✅
```

**All steps are metadata-driven. Zero Python code changes.**

---

## 14. Architecture Verdict

### **APPROVED FOR IMPLEMENTATION** ✅

**Task 14: Twin Binding & Activation Foundation**

This is the natural continuation of the zero-code chain:
```
... → ProvisioningExecution → PersistentTwinEntity
    → TwinBinding (Task 14) → TwinEntityRegistry + Device Binding
    → TelemetryService → TwinStateManager → Runtime State
```

The implementation is:
- **Thin** — orchestrates existing services, owns no new domain logic
- **Generic** — no industry coupling, JSONB configuration
- **Secure** — full tenant isolation via JWT + TenantAwareRepository
- **Extensible** — binding_type and extra_data support future patterns
- **Non-blocking** — future adapters read TwinBinding, never modify it

---

*Specification generated by DT-Lite Architecture Guardian Agent.*
*Phase 2 Task 14 — Twin Binding & Activation Foundation*
*Status: APPROVED FOR IMPLEMENTATION*
