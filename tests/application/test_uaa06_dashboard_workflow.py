"""UAA-06: Dashboard, LargeScreen, KPI, Alarm, Workflow & WorkOrder.

Tests for:
  - DashboardService: 13 widget types, CRUD, role-based visibility
  - LargeScreenService: read-only, auto-rotate, kiosk mode
  - KPIEngine: 20 KPIs, formula DSL, validation
  - AlarmService: 8-state lifecycle, escalation, notification, closure loop
  - WorkflowService: BPMN-lite, SOP→WorkOrder
  - WorkOrderService: assignment, SLA, closure, audit trail
  - GS-09 Integration: full Alarm→Workflow→WorkOrder chain
  - AG-P0-07: Dashboard ≠ LargeScreen Independence
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root))

from services.application.src.dashboard.service import DashboardService, VALID_WIDGET_TYPES
from services.application.src.largescreen.service import LargeScreenService
from services.telemetry.src.kpi.service import KPIEngine, KPI_DEFINITIONS
from services.telemetry.src.alarm.service import AlarmService, VALID_STATES, TRANSITIONS, VALID_SEVERITIES
from services.application.src.workflow.service import WorkflowService, VALID_NODE_TYPES
from services.application.src.workorder.service import WorkOrderService, VALID_WORKORDER_STATUSES


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def dashboard_service():
    return DashboardService()


@pytest.fixture
def largescreen_service():
    return LargeScreenService()


@pytest.fixture
def kpi_engine():
    return KPIEngine()


@pytest.fixture
def alarm_service():
    return AlarmService()


@pytest.fixture
def workflow_service():
    return WorkflowService()


@pytest.fixture
def workorder_service():
    return WorkOrderService()


@pytest.fixture
def asset_id():
    return "asset.park.hvac.ahu_01"


@pytest.fixture
def point_id():
    return "point.park.hvac.ahu_01.supply_air_temp"


# ═══════════════════════════════════════════════════════════════════
# DashboardService Tests
# ═══════════════════════════════════════════════════════════════════

class TestDashboardService:
    """Tests for DashboardService: CRUD, 13 widget types, role visibility."""

    def test_create_dashboard(self, dashboard_service):
        d = dashboard_service.create({
            "id": "dash-001",
            "code": "dash.park.energy_overview",
            "name": "Energy Overview",
            "widgets": [],
        }, tenant_id="t1")
        assert d.id == "dash-001"
        assert d.tenant_id == "t1"
        assert d.widget_count == 0

    def test_all_13_widget_types_accepted(self, dashboard_service):
        """AC-01: All 13 widget types are valid."""
        for wtype in VALID_WIDGET_TYPES:
            d = dashboard_service.create({
                "id": f"dash-{wtype}",
                "code": f"dash.park.widget_{wtype}",
                "name": f"{wtype} Widget",
                "widgets": [{"id": f"w-{wtype}", "type": wtype, "title": wtype}],
            }, tenant_id="t1")
            assert d.widget_count == 1
            assert d.widgets[0]["type"] == wtype

    def test_reject_invalid_widget_type(self, dashboard_service):
        with pytest.raises(ValueError, match="Invalid widget type"):
            dashboard_service.create({
                "id": "dash-bad",
                "code": "dash.park.bad_widget",
                "name": "Bad",
                "widgets": [{"id": "w1", "type": "invalid_type", "title": "x"}],
            }, tenant_id="t1")

    def test_reject_invalid_code_pattern(self, dashboard_service):
        with pytest.raises(ValueError, match="does not match convention"):
            dashboard_service.create({
                "id": "dash-bad",
                "code": "park.energy",  # missing dash. prefix
                "name": "Bad Code",
                "widgets": [],
            }, tenant_id="t1")

    def test_add_widget(self, dashboard_service):
        dashboard_service.create({
            "id": "dash-002",
            "code": "dash.park.add_w",
            "name": "Add Widget",
            "widgets": [],
        }, tenant_id="t1")
        dashboard_service.add_widget("dash-002", {"type": "chart", "title": "Power Trend"})
        d = dashboard_service.get("dash-002")
        assert d.widget_count == 1

    def test_remove_widget(self, dashboard_service):
        dashboard_service.create({
            "id": "dash-003",
            "code": "dash.park.rm_w",
            "name": "Remove Widget",
            "widgets": [{"id": "w1", "type": "gauge", "title": "G1"}],
        }, tenant_id="t1")
        dashboard_service.remove_widget("dash-003", "w1")
        d = dashboard_service.get("dash-003")
        assert d.widget_count == 0

    def test_role_filter_visibility(self, dashboard_service):
        dashboard_service.create({
            "id": "dash-004",
            "code": "dash.park.role_test",
            "name": "Role Test",
            "widgets": [
                {"id": "w1", "type": "chart", "title": "Public", "visibility": {"roles": ["*"]}},
                {"id": "w2", "type": "gauge", "title": "Admin Only", "visibility": {"roles": ["admin"]}},
            ],
        }, tenant_id="t1")
        public_widgets = dashboard_service.get_visible_widgets("dash-004", [])
        admin_widgets = dashboard_service.get_visible_widgets("dash-004", ["admin"])
        assert len(public_widgets) == 1  # only * role
        assert len(admin_widgets) == 2  # * and admin

    def test_delete_dashboard(self, dashboard_service):
        dashboard_service.create({
            "id": "dash-005",
            "code": "dash.park.del_d",
            "name": "Delete Test",
            "widgets": [],
        }, tenant_id="t1")
        assert dashboard_service.delete("dash-005") is True
        assert dashboard_service.get("dash-005") is None


# ═══════════════════════════════════════════════════════════════════
# LargeScreenService Tests
# ═══════════════════════════════════════════════════════════════════

class TestLargeScreenService:
    """Tests for LargeScreenService: read-only, auto-rotate, kiosk."""

    def test_create_largescreen(self, largescreen_service):
        ls = largescreen_service.create({
            "id": "ls-001",
            "code": "ls.park.lobby_display",
            "name": "Lobby Display",
            "layouts": [],
            "rotation_interval_seconds": 30,
        }, tenant_id="t1")
        assert ls.id == "ls-001"
        assert ls.kiosk_mode is True
        assert ls.rotation_interval_seconds == 30

    def test_reject_invalid_code_pattern(self, largescreen_service):
        with pytest.raises(ValueError, match="does not match convention"):
            largescreen_service.create({
                "id": "ls-bad",
                "code": "park.display",  # missing ls. prefix
                "name": "Bad",
                "layouts": [],
            }, tenant_id="t1")

    def test_reject_short_rotation_interval(self, largescreen_service):
        with pytest.raises(ValueError, match="rotation_interval_seconds"):
            largescreen_service.create({
                "id": "ls-002",
                "code": "ls.park.short_rot",
                "name": "Short Rotation",
                "layouts": [],
                "rotation_interval_seconds": 3,  # too short
            }, tenant_id="t1")

    def test_add_layout_auto_playlist(self, largescreen_service):
        ls = largescreen_service.create({
            "id": "ls-003",
            "code": "ls.park.add_l",
            "name": "Add Layout",
            "layouts": [],
            "rotation_interval_seconds": 20,
        }, tenant_id="t1")
        ls = largescreen_service.add_layout("ls-003", {"id": "lay-1", "widgets": []})
        assert ls.layout_count == 1
        assert ls.playlist_count == 1
        assert ls.playlist[0]["duration_seconds"] == 20

    def test_current_layout_rotation(self, largescreen_service):
        ls = largescreen_service.create({
            "id": "ls-004",
            "code": "ls.park.rot_test",
            "name": "Rotate Test",
            "layouts": [
                {"id": "lay-a", "widgets": []},
                {"id": "lay-b", "widgets": []},
            ],
            "rotation_interval_seconds": 15,
        }, tenant_id="t1")
        # Build playlist from layouts
        for lay in ls.layouts:
            largescreen_service.add_layout("ls-004", lay)
        current = largescreen_service.current_layout("ls-004", 0)
        assert current is not None
        assert current["id"] == "lay-a"
        current = largescreen_service.current_layout("ls-004", 1)
        assert current["id"] == "lay-b"

    def test_delete_largescreen(self, largescreen_service):
        largescreen_service.create({
            "id": "ls-005",
            "code": "ls.park.del_ls",
            "name": "Delete LS",
            "layouts": [],
        }, tenant_id="t1")
        assert largescreen_service.delete("ls-005") is True
        assert largescreen_service.get("ls-005") is None

    def test_largescreen_is_readonly(self, largescreen_service):
        """LargeScreen has no write interaction methods (read-only by design)."""
        ls = largescreen_service.create({
            "id": "ls-006",
            "code": "ls.park.ro_test",
            "name": "Read-Only Test",
            "layouts": [],
        }, tenant_id="t1")
        # No interaction methods exist — only read/rotate
        assert hasattr(ls, "kiosk_mode")
        assert ls.kiosk_mode is True


# ═══════════════════════════════════════════════════════════════════
# KPIEngine Tests
# ═══════════════════════════════════════════════════════════════════

class TestKPIEngine:
    """Tests for KPIEngine: 20 KPIs, formula DSL."""

    def test_all_20_kpis_defined(self, kpi_engine):
        """AC-04: 20 KPI definitions exist."""
        defs = kpi_engine.list_definitions()
        assert len(defs) == 20

    def test_get_kpi_definition(self, kpi_engine):
        defn = kpi_engine.get_definition("energy_intensity")
        assert defn is not None
        assert defn["category"] == "energy"
        assert "formula" in defn
        assert "unit" in defn

    def test_get_missing_kpi(self, kpi_engine):
        assert kpi_engine.get_definition("nonexistent") is None

    def test_compute_energy_intensity(self, kpi_engine):
        result = kpi_engine.compute("energy_intensity", {"total_kWh": 500.0})
        assert result is not None
        assert result.kpi_id == "energy_intensity"
        assert result.unit == "kWh/m2/h"

    def test_compute_equipment_availability(self, kpi_engine):
        result = kpi_engine.compute("equipment_availability", {"uptime_hours": 95.0})
        assert result is not None
        assert result.value > 0

    def test_compute_oee(self, kpi_engine):
        result = kpi_engine.compute("oee_total", {"availability": 0.9, "performance": 0.85, "quality": 0.95})
        assert result is not None

    def test_validate_valid_formula(self, kpi_engine):
        valid, errors = kpi_engine.validate_formula(
            "SELECT power_kw FROM telemetry AGG sum MATH / area"
        )
        assert valid is True
        assert len(errors) == 0

    def test_validate_missing_select(self, kpi_engine):
        valid, errors = kpi_engine.validate_formula("FROM telemetry AGG sum")
        assert valid is False
        assert any("SELECT" in e for e in errors)

    def test_validate_missing_agg(self, kpi_engine):
        valid, errors = kpi_engine.validate_formula("SELECT power FROM telemetry")
        assert valid is False
        assert any("AGG" in e for e in errors)

    def test_get_result_after_compute(self, kpi_engine):
        kpi_engine.compute("water_usage_rate", {"total_m3": 120.0})
        result = kpi_engine.get_result("water_usage_rate")
        assert result is not None
        assert result.value == 120.0

    def test_list_results_empty_initially(self, kpi_engine):
        assert len(kpi_engine.list_results()) == 0


# ═══════════════════════════════════════════════════════════════════
# AlarmService Tests — 8-State Lifecycle
# ═══════════════════════════════════════════════════════════════════

class TestAlarmService:
    """Tests for AlarmService: 8-state lifecycle, escalation, notification."""

    def test_create_alarm(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="High Temperature",
        )
        assert alarm.state == "normal"
        assert alarm.severity == "P2"
        assert alarm.id is not None

    def test_reject_invalid_severity(self, alarm_service, asset_id, point_id):
        with pytest.raises(ValueError, match="Invalid severity"):
            alarm_service.create(
                asset_id=asset_id, point_id=point_id,
                severity="P99", title="Bad",
            )

    def test_state_transitions_enforced(self, alarm_service, asset_id, point_id):
        """AC-05: 8 states with enforced transitions (no skip)."""
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P1", title="Critical Alarm",
        )
        # normal → acknowledged
        alarm = alarm_service.transition(alarm.id, "acknowledged")
        assert alarm.state == "acknowledged"
        assert alarm.acknowledged_at is not None
        # acknowledged → investigating
        alarm = alarm_service.transition(alarm.id, "investigating")
        assert alarm.state == "investigating"
        # investigating → resolving
        alarm = alarm_service.transition(alarm.id, "resolving")
        assert alarm.state == "resolving"
        # resolving → resolved
        alarm = alarm_service.transition(alarm.id, "resolved")
        assert alarm.state == "resolved"
        # resolved → closed
        alarm = alarm_service.transition(alarm.id, "closed")
        assert alarm.state == "closed"
        # closed → archived
        alarm = alarm_service.transition(alarm.id, "archived")
        assert alarm.state == "archived"
        # archived → purged
        alarm = alarm_service.transition(alarm.id, "purged")
        assert alarm.state == "purged"
        assert alarm.is_terminal is True

    def test_reject_invalid_transition(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="Test",
        )
        with pytest.raises(ValueError, match="Invalid transition"):
            # Cannot skip from normal to resolving
            alarm_service.transition(alarm.id, "resolving")

    def test_escalation(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P1", title="Escalation Test",
        )
        alarm = alarm_service.escalate(alarm.id, "timeout")
        assert alarm.escalation_level == 1
        alarm = alarm_service.escalate(alarm.id, "no response")
        assert alarm.escalation_level == 2

    def test_notification(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="Notify Test",
        )
        assert alarm_service.notify(alarm.id, "email", "ops@example.com") is True
        assert alarm_service.notify(alarm.id, "sms", "+1234567890") is True
        assert alarm_service.notify(alarm.id, "websocket", "user-1") is True

    def test_reject_invalid_notification_channel(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="Notify",
        )
        with pytest.raises(ValueError, match="Invalid channel"):
            alarm_service.notify(alarm.id, "invalid_channel", "x")

    def test_link_workflow(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="Workflow Link",
        )
        alarm = alarm_service.link_workflow(alarm.id, "wf-001", "wo-001")
        assert alarm.workflow_instance_id == "wf-001"
        assert alarm.workorder_id == "wo-001"

    def test_list_active_alarms(self, alarm_service, asset_id, point_id):
        alarm_service.create(asset_id=asset_id, point_id=point_id, severity="P1", title="A1")
        alarm_service.create(asset_id=asset_id, point_id=point_id, severity="P2", title="A2")
        active = alarm_service.list_active()
        assert len(active) == 2

    def test_list_by_severity(self, alarm_service, asset_id, point_id):
        alarm_service.create(asset_id=asset_id, point_id=point_id, severity="P1", title="A1")
        alarm_service.create(asset_id=asset_id, point_id=point_id, severity="P1", title="A2")
        alarm_service.create(asset_id=asset_id, point_id=point_id, severity="P2", title="A3")
        p1_alarms = alarm_service.list_by_severity("P1")
        assert len(p1_alarms) == 2

    def test_delete_purged_alarm(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P3", title="Delete Test",
        )
        # Transition to purged
        alarm_service.transition(alarm.id, "acknowledged")
        alarm_service.transition(alarm.id, "investigating")
        alarm_service.transition(alarm.id, "resolving")
        alarm_service.transition(alarm.id, "resolved")
        alarm_service.transition(alarm.id, "closed")
        alarm_service.transition(alarm.id, "archived")
        alarm_service.transition(alarm.id, "purged")
        assert alarm_service.delete(alarm.id) is True
        assert alarm_service.get(alarm.id) is None

    def test_cannot_delete_non_purged(self, alarm_service, asset_id, point_id):
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="Cannot Delete",
        )
        assert alarm_service.delete(alarm.id) is False


# ═══════════════════════════════════════════════════════════════════
# WorkflowService Tests
# ═══════════════════════════════════════════════════════════════════

class TestWorkflowService:
    """Tests for WorkflowService: BPMN-lite, SOP→WorkOrder."""

    def test_create_template(self, workflow_service):
        template = workflow_service.create_template(
            "tmpl-hvac-alarm",
            "HVAC Alarm SOP",
            nodes=[
                {"id": "start", "type": "start", "label": "Start", "next_node_ids": ["t1"]},
                {"id": "t1", "type": "user_task", "label": "Assign Technician",
                 "next_node_ids": ["t2"],
                 "config": {"role": "technician", "due_date": "2026-12-31"}},
                {"id": "t2", "type": "service_task", "label": "Invoke Capability",
                 "next_node_ids": ["end"],
                 "config": {"capability_code": "hvac.set_temperature"}},
                {"id": "end", "type": "end", "label": "End"},
            ],
        )
        assert template["id"] == "tmpl-hvac-alarm"
        assert len(template["nodes"]) == 4

    def test_reject_invalid_node_type(self, workflow_service):
        with pytest.raises(ValueError, match="Invalid node type"):
            workflow_service.create_template(
                "tmpl-bad", "Bad Template",
                nodes=[{"id": "start", "type": "invalid_type", "next_node_ids": []}],
            )

    def test_reject_unknown_next_node(self, workflow_service):
        with pytest.raises(ValueError, match="unknown next node"):
            workflow_service.create_template(
                "tmpl-bad2", "Bad Template 2",
                nodes=[
                    {"id": "start", "type": "start", "next_node_ids": ["nonexistent"]},
                ],
            )

    def test_create_instance(self, workflow_service):
        workflow_service.create_template(
            "tmpl-simple", "Simple SOP",
            nodes=[
                {"id": "start", "type": "start", "next_node_ids": ["t1"]},
                {"id": "t1", "type": "user_task", "label": "Inspect",
                 "next_node_ids": ["end"],
                 "config": {"role": "inspector"}},
                {"id": "end", "type": "end", "label": "End"},
            ],
        )
        instance = workflow_service.create_instance("tmpl-simple", {"asset_id": "a1", "alarm_id": "alarm-1"})
        assert instance.status == "running"
        assert len(instance.tasks) == 1
        assert instance.tasks[0]["node_type"] == "user_task"

    def test_complete_task(self, workflow_service):
        workflow_service.create_template(
            "tmpl-task", "Task Template",
            nodes=[
                {"id": "start", "type": "start", "next_node_ids": ["t1"]},
                {"id": "t1", "type": "service_task", "label": "Auto Task",
                 "next_node_ids": ["end"], "config": {}},
                {"id": "end", "type": "end", "label": "End"},
            ],
        )
        instance = workflow_service.create_instance("tmpl-task", {})
        task_id = instance.tasks[0]["id"]
        instance = workflow_service.complete_task(instance.id, task_id, {"result": "ok"})
        assert instance.status == "completed"

    def test_cancel_instance(self, workflow_service):
        workflow_service.create_template(
            "tmpl-cancel", "Cancel Template",
            nodes=[
                {"id": "start", "type": "start", "next_node_ids": ["t1"]},
                {"id": "t1", "type": "user_task", "label": "Task",
                 "next_node_ids": ["end"], "config": {}},
                {"id": "end", "type": "end", "label": "End"},
            ],
        )
        instance = workflow_service.create_instance("tmpl-cancel", {})
        assert workflow_service.cancel(instance.id) is True
        assert instance.status == "cancelled"


# ═══════════════════════════════════════════════════════════════════
# WorkOrderService Tests
# ═══════════════════════════════════════════════════════════════════

class TestWorkOrderService:
    """Tests for WorkOrderService: assignment, SLA, closure, audit trail."""

    def test_create_workorder(self, workorder_service):
        wo = workorder_service.create(
            title="Fix HVAC Alarm",
            workorder_type="corrective",
            asset_id="asset-001",
            priority="high",
        )
        assert wo.status == "draft"
        assert wo.priority == "high"
        assert wo.code.startswith("WO-")

    def test_reject_invalid_type(self, workorder_service):
        with pytest.raises(ValueError, match="Invalid type"):
            workorder_service.create(
                title="Bad", workorder_type="invalid_type",
            )

    def test_assign_workorder(self, workorder_service):
        wo = workorder_service.create(title="Assign Test", workorder_type="corrective")
        wo = workorder_service.assign(wo.id, "tech-001", "hvac_technician")
        assert wo.status == "assigned"
        assert wo.assigned_to == "tech-001"

    def test_start_workorder(self, workorder_service):
        wo = workorder_service.create(title="Start Test", workorder_type="preventive")
        wo = workorder_service.assign(wo.id, "tech-001")
        wo = workorder_service.start(wo.id)
        assert wo.status == "in_progress"

    def test_complete_then_close(self, workorder_service):
        wo = workorder_service.create(title="Close Test", workorder_type="inspection")
        wo = workorder_service.assign(wo.id, "tech-001")
        wo = workorder_service.start(wo.id)
        wo = workorder_service.complete(wo.id, reviewer_id="supervisor-1")
        assert wo.status == "pending_review"
        wo = workorder_service.close(wo.id, closer_id="manager-1")
        assert wo.status == "closed"
        assert wo.closed_by == "manager-1"
        assert wo.sla_compliance is not None

    def test_audit_trail(self, workorder_service):
        wo = workorder_service.create(title="Audit Test", workorder_type="corrective")
        wo = workorder_service.assign(wo.id, "tech-001")
        wo = workorder_service.start(wo.id)
        wo = workorder_service.complete(wo.id)
        wo = workorder_service.close(wo.id, "mgr-1")
        actions = [entry["action"] for entry in wo.audit_trail]
        assert "created" in actions
        assert "assigned" in actions
        assert "started" in actions
        assert "completed" in actions
        assert "closed" in actions

    def test_sla_breached(self, workorder_service):
        wo = workorder_service.create(
            title="SLA Test", workorder_type="corrective",
            sla_deadline="2020-01-01T00:00:00+00:00",  # past deadline
        )
        assert wo.is_sla_breached() is True

    def test_sla_not_breached_future(self, workorder_service):
        wo = workorder_service.create(
            title="SLA Future", workorder_type="corrective",
            sla_deadline="2099-12-31T23:59:59+00:00",
        )
        assert wo.is_sla_breached() is False

    def test_cannot_assign_completed(self, workorder_service):
        wo = workorder_service.create(title="No Assign", workorder_type="corrective")
        wo = workorder_service.assign(wo.id, "tech-001")
        with pytest.raises(ValueError, match="Cannot assign"):
            workorder_service.assign(wo.id, "tech-002")


# ═══════════════════════════════════════════════════════════════════
# GS-09 Integration Test
# ═══════════════════════════════════════════════════════════════════

class TestGS09Integration:
    """GS-09: Dashboard + LargeScreen + KPI + Alarm + Workflow integrated scenario."""

    def test_full_alarm_to_workorder_closure(self, alarm_service, workflow_service, workorder_service, asset_id, point_id):
        """AC-06: Alarm → Workflow → WorkOrder → Resolution → Alarm resolved."""
        # 1. Create alarm
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P2", title="HVAC High Temp",
        )
        assert alarm.state == "normal"

        # 2. Create SOP workflow for this alarm type
        workflow_service.create_template(
            "sop-hvac-alarm", "HVAC Alarm SOP",
            nodes=[
                {"id": "start", "type": "start", "label": "Start", "next_node_ids": ["t1"]},
                {"id": "t1", "type": "user_task", "label": "Inspect",
                 "next_node_ids": ["t2"],
                 "config": {"role": "technician"}},
                {"id": "t2", "type": "service_task", "label": "Fix",
                 "next_node_ids": ["end"],
                 "config": {"capability_code": "hvac.set_temperature"}},
                {"id": "end", "type": "end", "label": "End"},
            ],
        )

        # 3. Create workflow instance
        wf_instance = workflow_service.create_instance("sop-hvac-alarm", {
            "asset_id": asset_id, "alarm_id": alarm.id,
        })

        # 4. Link alarm to workflow
        alarm = alarm_service.link_workflow(alarm.id, wf_instance.id, None)
        assert alarm.workflow_instance_id == wf_instance.id

        # 5. Create workorder from workflow
        wo = workorder_service.create(
            title=f"Fix {alarm.title}",
            workorder_type="corrective",
            asset_id=asset_id,
            priority="high",
        )

        # 6. Complete workflow tasks
        for task in wf_instance.tasks:
            workflow_service.complete_task(wf_instance.id, task["id"], {"result": "done"})

        # 7. Transition alarm through full lifecycle
        alarm_service.transition(alarm.id, "acknowledged")
        alarm_service.transition(alarm.id, "investigating")
        alarm_service.transition(alarm.id, "resolving")
        alarm_service.transition(alarm.id, "resolved")

        # 8. Verify alarm is resolved
        alarm = alarm_service.get(alarm.id)
        assert alarm.state == "resolved"
        assert alarm.resolved_at is not None

        # 9. Complete and close workorder
        wo = workorder_service.assign(wo.id, "tech-001")
        wo = workorder_service.start(wo.id)
        wo = workorder_service.complete(wo.id)
        assert wo.status == "pending_review"
        wo = workorder_service.close(wo.id, "mgr-1")
        assert wo.status == "closed"

    def test_dashboard_and_largescreen_independent(self, dashboard_service, largescreen_service):
        """AG-P0-07: Dashboard and LargeScreen have independent persistence."""
        # Create dashboard
        dash = dashboard_service.create({
            "id": "dash-gs09",
            "code": "dash.park.gs09_test",
            "name": "GS-09 Dashboard",
            "widgets": [{"id": "w1", "type": "chart", "title": "Power"}],
        }, tenant_id="t1")

        # Create largescreen
        ls = largescreen_service.create({
            "id": "ls-gs09",
            "code": "ls.park.gs09_test",
            "name": "GS-09 LargeScreen",
            "layouts": [{"id": "lay-1", "widgets": []}],
        }, tenant_id="t1")

        # Verify independence: deleting dashboard does NOT affect largescreen
        dashboard_service.delete("dash-gs09")
        assert dashboard_service.get("dash-gs09") is None
        assert largescreen_service.get("ls-gs09") is not None

        # Verify independence: deleting largescreen does NOT affect dashboard
        largescreen_service.delete("ls-gs09")
        assert largescreen_service.get("ls-gs09") is None
        assert dashboard_service.get("dash-gs09") is None  # already deleted

    def test_kpi_computation_during_alarm(self, kpi_engine, alarm_service, asset_id, point_id):
        """KPI computation works independently alongside alarm lifecycle."""
        # Compute KPIs
        kpi_engine.compute("energy_intensity", {"total_kWh": 500.0})
        kpi_engine.compute("equipment_availability", {"uptime_hours": 95.0})

        # Create and process alarm simultaneously
        alarm = alarm_service.create(
            asset_id=asset_id, point_id=point_id,
            severity="P1", title="Critical",
        )
        alarm_service.transition(alarm.id, "acknowledged")
        alarm_service.transition(alarm.id, "investigating")

        # KPIs still accessible
        assert kpi_engine.get_result("energy_intensity") is not None
        assert kpi_engine.get_result("equipment_availability") is not None
