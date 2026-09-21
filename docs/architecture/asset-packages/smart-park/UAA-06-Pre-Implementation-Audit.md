# UAA-06 Pre-Implementation Audit

**Task**: UAA-06: Dashboard, LargeScreen, KPI, Alarm, Workflow & WorkOrder
**Date**: 2026-09-13
**Base Line**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Predecessors**: UAA-01~05 (all passing)

---

## 1. Architecture Gate Target

| Gate | Check | Expected |
|------|-------|----------|
| **AG-P0-07** | Dashboard ≠ LargeScreen Independence | Different tables, different APIs, different permission models |
| AG-P1-01 | Unit Test Coverage ≥ 80% | Core services only |
| AG-P1-02 | Integration Test Coverage ≥ 70% | GS-09 API contracts |

## 2. Scope Lock Compliance Checklist

| SL | Prohibition | UAA-06 Compliance |
|----|-------------|-------------------|
| SL-01 | No new fields in Universal Contract Objects | ✅ Dashboard/LargeScreen/KPI/Alarm/Workflow are NEW objects |
| SL-03 | No mandatory industry fields in Universal Contract | ✅ All field names are generic (type, state, config) |
| SL-09 | No Dashboard/LargeScreen conflation | ✅ HARD RULE: Different tables, APIs, permission models |
| SL-12 | No weakening Contract constraints | ✅ All existing constraints preserved |

## 3. Dashboard vs LargeScreen (INDEPENDENT — SL-09 / AG-P0-07)

### 3.1 Dashboard
- **Tables**: `dashboard`, `dashboard_widget`, `dashboard_permission`
- **Nature**: Interactive, multi-user, role-filtered, drill-down
- **Data Flow**: WebSocket real-time updates
- **Widgets**: 13 types (chart, gauge, table, map, 3d, alarm_list, kpi_card, trend, heatmap, list, filter, metric, custom)
- **Permissions**: Role-based visibility per widget
- **Drill-down**: Widget → Asset → Point → Raw telemetry

### 3.2 LargeScreen
- **Tables**: `largescreen`, `largescreen_layout`, `largescreen_playlist`
- **Nature**: Read-only, single-layout, auto-rotate, kiosk-mode
- **Data Flow**: WebSocket broadcast (push-only, no user input)
- **Auto-rotate**: Playlist of layouts, configurable interval
- **Kiosk**: Full-screen, no user interaction, TV/wall display
- **No permissions**: Public read-only access

### 3.3 Separation Matrix
| Aspect | Dashboard | LargeScreen |
|--------|-----------|-------------|
| Persistence | dashboard, dashboard_widget, dashboard_permission | largescreen, largescreen_layout, largescreen_playlist |
| API | `/api/v2/dashboard/*` | `/api/v2/largescreen/*` |
| Permission | RBAC + widget-level | None (public read-only) |
| WebSocket | Subscribe to specific data | Broadcast to all viewers |
| Interaction | Click, filter, drill-down | None (read-only) |
| Layout | Dynamic (user-configured) | Static (pre-defined) |
| Rotation | No | Auto-rotate playlist |

## 4. KPI Engine (20 KPIs)

### 4.1 KPI Definitions

| KPI ID | Name | Category | Formula |
|--------|------|----------|---------|
| KPI-01 | energy_intensity | Energy | total_kWh / floor_area_m2 |
| KPI-02 | equipment_availability | Production | uptime_hours / (uptime+downtime) |
| KPI-03 | occupant_comfort | Environment | avg(thermal_index, air_quality_index) |
| KPI-04 | water_usage_rate | Water | m3 / day |
| KPI-05 | security_incident_rate | Security | incidents / 1000_persons |
| KPI-06 | parking_occupancy | Transport | occupied_spaces / total_spaces |
| KPI-07 | hvac_efficiency | HVAC | cooling_output_kWh / electrical_input_kWh |
| KPI-08 | fire_alarm_response_time | Fire | avg(seconds from alarm to response) |
| KPI-09 | oee_total | Production | availability × performance × quality |
| KPI-10 | carbon_footprint | Environment | total_CO2_kg / floor_area_m2 |
| KPI-11 | light_level_compliance | Lighting | % areas meeting lux standard |
| KPI-12 | elevator_availability | Elevator | uptime_hours / total_hours |
| KPI-13 | access_control_pass_rate | Access | successful_reads / total_reads |
| KPI-14 | waste_collection_rate | Waste | collections_on_time / total_scheduled |
| KPI-15 | green_space_ratio | Green | green_area_m2 / total_area_m2 |
| KPI-16 | it_uptime | IT | server_online_hours / total_hours |
| KPI-17 | network_latency_p95 | IT | 95th percentile response time |
| KPI-18 | tenant_satisfaction | Facility | survey_score / 5.0 |
| KPI-19 | emergency_evacuation_time | Fire | avg(seconds to clear zone) |
| KPI-20 | cost_per_sqm | Energy | total_operating_cost / floor_area_m2 |

### 4.2 Formula DSL
```
SELECT <metric> FROM <source>
WHERE <conditions>
TIME_WINDOW <window>
AGG <sum|avg|min|max|count|latest>
FILTER <role|zone|category>
MATH <operation>
```

## 5. Alarm Engine (8 States)

### 5.1 State Machine
```
normal → acknowledged → investigating → resolving → resolved → closed → archived → purged
   ↑                                                                       ↓
   └──────────── escalate (time/severity) ←─────────────────────────────────┘
```

### 5.2 State Transition Rules
| From | To | Condition |
|------|-----|-----------|
| normal | acknowledged | Alarm triggered, auto-transition on detection |
| acknowledged | investigating | Operator acknowledges and starts investigation |
| investigating | resolving | Root cause identified, fix in progress |
| resolving | resolved | Fix applied, verification passed |
| resolved | closed | Approval workflow complete |
| closed | archived | 30-day retention, auto-archive |
| archived | purged | 90-day retention, auto-purge |
| Any | normal | Manual reset (admin only) |

### 5.3 Escalation Matrix
| Severity | 5min | 15min | 30min | 1hr |
|----------|------|-------|-------|-----|
| P1 (Critical) | Supervisor | Manager | Director | Emergency Team |
| P2 (High) | Team Lead | Supervisor | Manager | — |
| P3 (Medium) | Team Lead | Supervisor | — | — |
| P4 (Low) | — | Team Lead | — | — |

### 5.4 Notification Channels
- Email, SMS, WebSocket push, PagerDuty, Webhook

## 6. Alarm → Workflow → WorkOrder Closure Loop

```
Alarm.triggered
  → Alarm state → investigating
  → SOP lookup (alarm_type → workflow_template)
  → Workflow.create(instance)
  → WorkOrder.create(from workflow task)
  → WorkOrder.assign(technician)
  → Technician completes work
  → WorkOrder.closed
  → Workflow.mark_resolved
  → Alarm.state → resolved
  → Alarm.state → closed (after approval)
```

## 7. Workflow Engine (BPMN-lite)

### 7.1 Node Types
| Type | Description |
|------|-------------|
| start | Workflow entry point |
| user_task | Human assignee, form_schema, due_date |
| service_task | Auto: capability_invocation, script, webhook |
| gateway | Exclusive (XOR) / Parallel (AND) split |
| end | Workflow completion |
| timer_boundary | Time-based trigger or timeout |

### 7.2 Variable Persistence
- Workflow context variables: `{technician_id, asset_id, alarm_id, resolution_notes, ...}`
- Persisted to `workflow_variables` table (JSONB)

## 8. WorkOrder Service

### 8.1 Fields
- `id`, `code`, `title`, `type`, `status`, `priority`, `asset_id`, `assigned_to`
- `sla_deadline`, `sla_compliance` (boolean)
- `created_by`, `closed_by`
- `audit_trail` (append-only list of status changes)

### 8.2 Status Lifecycle
```
draft → assigned → in_progress → pending_review → completed → closed
```

## 9. GS-09 Integration Test

End-to-end scenario:
1. Create Dashboard with 5 widgets (chart, gauge, alarm_list, kpi_card, 3d)
2. Create LargeScreen with 3-layout auto-rotate playlist
3. Trigger KPI computation (energy_intensity, equipment_availability)
4. Simulate Alarm (P2 severity) → auto-escalate at 15min
5. Create Workflow (SOP for HVAC alarm) → generate WorkOrder
6. Complete WorkOrder → auto-close Alarm → verify state chain
7. Verify Dashboard ≠ LargeScreen: different API endpoints, different permissions

## 10. Pre-Implementation Checklist

### Dashboard vs LargeScreen (INDEPENDENT)
- [x] Dashboard tables: dashboard, dashboard_widget, dashboard_permission
- [x] LargeScreen tables: largescreen, largescreen_layout, largescreen_playlist
- [x] NO shared tables, NO shared base class
- [x] Dashboard: interactive, multi-user, drill-down, real-time WebSocket
- [x] LargeScreen: read-only, single layout, auto-rotate, WebSocket broadcast only

### KPI Engine
- [x] 20 KPIs defined
- [x] Formula DSL: SELECT, AGG, TIME_WINDOW, FILTER, MATH
- [x] Real-time (streaming) + Scheduled (cron) computation modes

### Alarm Engine
- [x] 8 states with enforced transitions (no skip)
- [x] Escalation: time-based + severity-based + acknowledgment-based
- [x] Closure loop: Alarm → SOP → WorkOrder → Resolution → Alarm.resolved

### Workflow/WorkOrder
- [x] SOP Template → Workflow Instance → WorkOrder(s)
- [x] Human tasks: assignee, role, due_date, form_schema
- [x] Auto tasks: capability_invocation, script, webhook

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alarm state transition bypass | Medium | High | Enum enforcement + state machine validation |
| Dashboard/LargeScreen conflation | Low | Medium | Separate service classes, no shared base |
| KPI formula DSL complexity | Medium | Low | Simple DSL, no SQL injection (parameterized) |
| Workflow circular dependency | Low | Medium | DAG validation on workflow creation |

## 12. Design Lock Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pre-Implementation Audit | agnes_flash | 2026-09-13 | _(pending)_ |
| Design Lock Review | dt_manager | _(pending)_ | _(pending)_ |
| ARB Final Sign-off | _(pending)_ | _(pending)_ | _(pending)_ |

---

**Design Lock Status**: PENDING REVIEW
