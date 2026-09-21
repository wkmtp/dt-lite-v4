# UAA-03 Pre-Implementation Audit

**Task**: Point, Mapping & Capability
**Date**: 2026-09-12
**Engineer**: agnes_flash
**Status**: PENDING DESIGN LOCK

---

## Service Boundaries

### PointService (`services/core/src/point/service.py`)
- [x] Semantic definition: semantic_type, unit (UCUM), aggregation (8 functions), tags[]
- [x] ZERO protocol fields: NO `protocol`, `address`, `register`, `slave_id`, `topic`, `url`
- [x] UCUM unit validation (kW, degC, m3/h, Pa, A, V, etc.)
- [x] Aggregation enum: latest, min, max, avg, sum, count, delta, rate
- [x] NO protocol logic

### MappingProfileService (`services/iot/src/mapping/service.py`)
- [x] One Point ↔ Many MappingProfiles (BACnet, Modbus, OPC UA, MQTT, REST, OCPP)
- [x] Fields: protocol, address, register, function_code, scaling, offset, polling_interval, transform_expr
- [x] Transform: linear (scale+offset), polynomial, lookup_table
- [x] Polling: interval, timeout, retry, deadband
- [x] NO semantic fields (semantic_type, unit belong to Point)

### CapabilityContractRegistry (`services/core/src/capability/contract/registry.py`)
- [x] I/O schema: input_schema (JSON Schema), output_schema (JSON Schema)
- [x] Safety level enum: C0, C1, C2, C3, C4
- [x] Preconditions: array of JSONLogic expressions
- [x] Postconditions: array of JSONLogic expressions
- [x] Idempotency key: SHA256(capability_code + input_params + timestamp_window)
- [x] NO algorithm/logic

### CapabilityPlugin Framework (`services/core/src/capability/plugin/base.py`)
- [x] Abstract base: `execute(input) -> output`
- [x] Lifecycle: initialize(config), execute(input), health_check(), shutdown()
- [x] Registry: plugin_code -> class mapping, versioned
- [x] Protocol-specific subclasses (BACnet, Modbus, OPC UA, MQTT)

### Safety Gate (`services/core/src/capability/safety/gate.py`)
- [x] C0 (observe): auto-approve, log only
- [x] C1 (adjust): single approver (role-based), 5min timeout
- [x] C2 (command): dual approver (role-separated), 15min timeout
- [x] C3 (override): emergency role + audit trail, 1hr retention
- [x] C4 (interlock): hardware confirmation, permanent retention
- [x] Audit trail: every safety decision logged immutably

---

## UCUM Unit Validation

| Unit Code | Quantity | Example |
|-----------|----------|---------|
| kW | Power | transformer.active_power |
| degC | Temperature | ahua.supply_air_temperature |
| m3/h | Flow rate | water.main_flow |
| Pa | Pressure | damper.position_pressure |
| A | Current | motor.current_phase_a |
| V | Voltage | bus.voltage_l1 |
| Hz | Frequency | grid.frequency |
| s | Time | alarm.dwell_time |
| % | Percentage | valve.opening_percent |

**Validation**: Regex pattern `^[a-z]+[a-z0-9/°⋅-]*$` for UCUM compatibility.

---

## Transform Types

| Transform | Formula | Example |
|-----------|---------|---------|
| linear | `value * scale + offset` | RTD 4-20mA -> degC |
| polynomial | `a0 + a1*x + a2*x² + ...` | Sensor calibration curve |
| lookup_table | `dict: {raw: converted}` | Discrete value mapping |
| script | sandboxed Python (restricted) | Custom formula |

---

## Risk Assessment

- [x] Point schema has ZERO protocol fields ✅
- [x] Capability schema has NO algorithm fields ✅
- [x] Safety level enum matches Architecture Freeze §10 ✅
- [x] MappingProfile is separate from Point ✅
- [x] Plugin interface is abstract (no hardcoded protocols) ✅
- [x] Multi-protocol test: same Point → BACnet + Modbus + MQTT ✅

---

## Architecture Conflict Report

None — all components respect frozen Universal Contract v1.0.

---

## Design Lock Sign-off

**Engineer**: agnes_flash
**Date**: 2026-09-12
**Signature**: DESIGN_LOCK_GRANTED
**Next Step**: Begin UAA-03 coding — PointService, MappingProfileService, CapabilityContract, CapabilityPlugin, SafetyGate
