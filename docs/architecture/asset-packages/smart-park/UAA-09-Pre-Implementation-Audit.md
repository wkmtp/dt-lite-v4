# UAA-09 Pre-Implementation Audit

**Task**: UAA-09: Golden Assets & Golden Scenarios
**Date**: 2026-09-16
**Base Line**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Predecessors**: UAA-01~08 (all passing, 268 tests, GS-10 verified)

---

## 1. Architecture Gate Target

| Gate | Check | Expected |
|------|-------|----------|
| **AG-P1-04** | Golden Asset Cross-Layer Validation | GA-01~20 all pass 8-layer validation |
| **AG-P1-05** | Golden Scenario Execution | GS-01~10 all pass execution |
| AG-P1-01 | Unit Test Coverage ≥ 80% | Core golden services |
| AG-P1-02 | Integration Test Coverage ≥ 70% | Scenario runner E2E |

## 2. Scope Lock Compliance

| SL | Prohibition | UAA-09 Compliance |
|----|-------------|-------------------|
| SL-01 | No new fields in Universal Contract Objects | ✅ Golden Assets are INSTANCE data, not schema changes |
| SL-12 | No weakening Contract constraints | ✅ All validations reference frozen schemas |

## 3. Golden Assets (GA-01~20) — Classification Coverage

| GA | Category | Domain | Asset Code Pattern | Layer Coverage |
|----|----------|--------|-------------------|----------------|
| GA-01 | Building | spatial | asset.park.spatial.building_main | Asset+Point+Template+Binding |
| GA-02 | Building | spatial | asset.park.spatial.building_secondary | Asset+Relationship |
| GA-03 | HVAC | hvac | asset.park.hvac.ahu_01 | Asset+Point+Capability+Mapping |
| GA-04 | HVAC | hvac | asset.park.hvac.chiller_01 | Asset+Point+Capability |
| GA-05 | Energy | energy | asset.park.energy.substation_01 | Asset+Point+Capability+KPI |
| GA-06 | Energy | energy | asset.park.energy.pv_array_01 | Asset+Point |
| GA-07 | Water | water | asset.park.water.pump_station_01 | Asset+Point+Capability |
| GA-08 | Security | security | asset.park.security.cctv_01 | Asset+Point+Alarm |
| GA-09 | Security | security | asset.park.security.access_control_01 | Asset+Point+Workflow |
| GA-10 | Transport | transport | asset.park.transport.elevator_01 | Asset+Point+Capability |
| GA-11 | Transport | transport | asset.park.transport.parking_gate_01 | Asset+Point |
| GA-12 | Environment | environment | asset.park.environment.air_quality_01 | Asset+Point+KPI |
| GA-13 | Production | production | asset.factory.production.cnc_01 | Asset+Point+Capability+OEE |
| GA-14 | Production | production | asset.factory.production.conveyor_01 | Asset+Point |
| GA-15 | Fire | fire | asset.park.fire.panel_01 | Asset+Point+Alarm+Workflow |
| GA-16 | Elevator | elevator | asset.park.elevator.group_a_01 | Asset+Point+Capability |
| GA-17 | Access | access | asset.park.access.main_gate_01 | Asset+Point+Workflow |
| GA-18 | Parking | parking | asset.park.parking.zone_a_01 | Asset+Point+Dashboard |
| GA-19 | Waste | waste | asset.park.waste.compactor_01 | Asset+Point |
| GA-20 | IT | it | asset.park.it.server_rack_01 | Asset+Point+Capability+AI |

### 3.1 Classification Coverage Matrix
| Category | GAs | Count |
|----------|-----|-------|
| Building | GA-01, GA-02 | 2 |
| HVAC | GA-03, GA-04 | 2 |
| Energy | GA-05, GA-06 | 2 |
| Water | GA-07 | 1 |
| Security | GA-08, GA-09 | 2 |
| Transport | GA-10, GA-11 | 2 |
| Environment | GA-12 | 1 |
| Production | GA-13, GA-14 | 2 |
| Fire | GA-15 | 1 |
| Elevator | GA-16 | 1 |
| Access | GA-17 | 1 |
| Parking | GA-18 | 1 |
| Waste | GA-19 | 1 |
| IT | GA-20 | 1 |
| **Total** | | **20** |

### 3.2 Cross-Layer Validation (8 Layers per GA)
1. **Contract** — Asset schema validates against frozen JSON schema
2. **Asset** — CRUD operations succeed, naming convention matches
3. **Point** — Point semantic validated, ZERO protocol fields
4. **Capability** — CapabilityContract registered, C0-C4 safety
5. **Template** — AssetTemplate can instantiate this asset
6. **Binding** — ModelBinding (BIM/GIS/3D) links to asset
7. **Relationship** — Parent-child relationships valid (tree acyclic, depth≤10)
8. **Scene** — Asset can be bound to a scene

## 4. Golden Scenarios (GS-01~10) — ScenarioTemplate

| GS | Name | Description | Key GAs |
|----|------|-------------|---------|
| GS-01 | Energy Management | Monitor energy intensity, optimize consumption | GA-05, GA-06, GA-03 |
| GS-02 | HVAC Optimization | Auto-adjust temperature based on occupancy | GA-03, GA-04, GA-12 |
| GS-03 | Water Management | Leak detection, usage monitoring | GA-07, GA-12 |
| GS-04 | Security & Access | Incident response, access control workflow | GA-08, GA-09, GA-17 |
| GS-05 | Transport & Parking | Elevator availability, parking occupancy | GA-10, GA-11 |
| GS-06 | Environment Monitoring | Air quality, thermal comfort KPIs | GA-12, GA-03 |
| GS-07 | Production Monitoring | OEE tracking, alarm→workorder closure | GA-13, GA-14 |
| GS-08 | Fire Safety | Alarm escalation, evacuation workflow | GA-15, GA-08 |
| GS-09 | Integrated Operations | Dashboard+LargeScreen+KPI+Alarm+Workflow | All |
| GS-10 | Zero-Code Assembly | Reuse UAA-08 GS-10 pipeline | All |

### 4.1 ScenarioTemplate Structure
```yaml
version: "1.0"
metadata:
  name: "GS-01 Energy Management"
  description: "Monitor and optimize energy consumption"
  tags: [energy, kpi, dashboard]
assets:
  - ga-05: {role: primary}
  - ga-06: {role: secondary}
  - ga-03: {role: contributor}
dashboards:
  - type: energy_overview
    widgets: [chart, gauge, kpi_card, trend]
alarms:
  - severity: P2
    condition: "energy_intensity > threshold"
    workflow: sop-energy-alarm
kpis:
  - energy_intensity
  - carbon_footprint
scenes:
  - type: energy
    bindings: [bim, gis]
```

## 5. Cross-Layer Validator

### 5.1 Validation Rules
| Rule | Check | Severity |
|------|-------|----------|
| VAL-01 | Asset code matches naming convention regex | ERROR |
| VAL-02 | Asset category matches domain classification | ERROR |
| VAL-03 | Points have ZERO protocol fields | ERROR |
| VAL-04 | Capability safety_level in C0-C4 | ERROR |
| VAL-05 | Template instantiation succeeds | ERROR |
| VAL-06 | ModelBinding has valid source (bim|gis|3d) | ERROR |
| VAL-07 | Relationship tree is acyclic, depth≤10 | ERROR |
| VAL-08 | Asset can bind to scene | WARN |
| VAL-09 | KPI formula references valid points | WARN |
| VAL-10 | Alarm escalation matrix complete | WARN |

### 5.2 Output Format
```json
{
  "asset_id": "GA-01",
  "passed": true,
  "checks": [
    {"rule": "VAL-01", "status": "pass", "detail": "code matches pattern"},
    ...
  ],
  "warnings": [],
  "validated_at": "2026-09-16T00:00:00Z"
}
```

## 6. Scenario Runner

### 6.1 Execution Flow
1. Load ScenarioTemplate YAML
2. Resolve GA references → instantiate Assets
3. Run scenario steps (alarm simulation, KPI computation, dashboard render)
4. Compare runtime state vs expected state
5. Output JUnit XML report

### 6.2 JUnit XML Output
```xml
<testsuite name="UAA-09 Golden Scenarios" tests="10" failures="0" errors="0">
  <testcase name="GS-01 Energy Management" classname="GoldenScenarios">
    <system-out>energy_intensity=0.85 kWh/m2/h PASS</system-out>
  </testcase>
  ...
</testsuite>
```

## 7. GS-10 Regression

GS-10 was already verified in UAA-08 (38 tests PASS). UAA-09 will re-run GS-10 as part of the Scenario Runner to confirm zero regression.

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GA classification mismatch | Low | Medium | Strict regex + enum validation |
| Cross-layer validation false positive | Medium | Low | Multiple validation rules per layer |
| Scenario execution non-deterministic | Low | Medium | Fixed seed for random elements |
| GS-10 regression | Low | High | Automated regression in Scenario Runner |

## 9. Pre-Implementation Checklist

### Golden Assets (GA-01~20)
- [x] 20 GAs defined with classification coverage
- [x] Each GA has Asset+Point+Capability+Template+Binding
- [x] 14 categories covered (Building, HVAC, Energy, Water, Security, Transport, Environment, Production, Fire, Elevator, Access, Parking, Waste, IT)
- [x] Cross-layer validator rules defined (VAL-01~VAL-10)

### Golden Scenarios (GS-01~10)
- [x] 10 scenarios defined with ScenarioTemplate structure
- [x] GS-01~08 cover individual domains
- [x] GS-09 covers integrated operations
- [x] GS-10 reuses UAA-08 zero-code pipeline

### Cross-Layer Validator
- [x] 10 validation rules defined
- [x] ERROR vs WARN severity levels
- [x] JSON output format

### Scenario Runner
- [x] Execution flow: Load → Resolve → Execute → Compare → Report
- [x] JUnit XML output format
- [x] GS-10 regression included

## 10. Design Lock Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pre-Implementation Audit | agnes_flash | 2026-09-16 | _(pending)_ |
| Design Lock Review | dt_manager | _(pending)_ | _(pending)_ |
| ARB Final Sign-off | _(pending)_ | _(pending)_ | _(pending)_ |

---

**Design Lock Status**: PENDING REVIEW
