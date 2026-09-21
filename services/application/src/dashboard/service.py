"""Dashboard Service — Interactive, widget-based, role-filtered dashboards.

Separate from LargeScreen (SL-09 / AG-P0-07):
  - Dashboard: interactive, multi-user, drill-down, real-time WebSocket
  - LargeScreen: read-only, auto-rotate, kiosk, TV/wall display
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

DASHBOARD_CODE_PATTERN = re.compile(r"^dash\.(park|factory)\.[a-z_][a-z0-9_]*$")

VALID_WIDGET_TYPES = {
    "chart", "gauge", "table", "map", "3d",
    "alarm_list", "kpi_card", "trend", "heatmap",
    "list", "filter", "metric", "custom",
}


@dataclass
class Widget:
    """A single widget within a dashboard."""
    id: str
    type: str  # one of VALID_WIDGET_TYPES
    title: str
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(default_factory=dict)  # {row, col, span_x, span_y}
    visibility: dict[str, Any] = field(default_factory=dict)  # {roles: [...], conditions: [...]}


@dataclass
class Dashboard:
    """Dashboard entity — interactive, role-filtered, widget-based."""
    id: str
    code: str
    name: str
    tenant_id: str
    widgets: list[dict[str, Any]] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)  # {roles: [...], view_mode: read|edit}
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def widget_count(self) -> int:
        return len(self.widgets)

    @property
    def created_at(self) -> str:
        return self.metadata.get("created_at", "")


class DashboardService:
    """Dashboard service: CRUD, widget management, role-based visibility.

    NO 3D rendering (ThreeRuntime), NO large-screen auto-rotate (LargeScreenService).
    """

    def __init__(self) -> None:
        self._dashboards: dict[str, Dashboard] = {}

    def create(self, data: dict[str, Any], tenant_id: str) -> Dashboard:
        """Create a dashboard with validation."""
        for key in ["id", "code", "name"]:
            if key not in data:
                raise ValueError(f"Dashboard missing required field: {key}")

        if not DASHBOARD_CODE_PATTERN.match(data["code"]):
            raise ValueError(
                f"Dashboard code '{data['code']}' does not match convention: "
                f"dash.<domain>.<type>"
            )

        widgets = data.get("widgets", [])
        for w in widgets:
            if w.get("type") not in VALID_WIDGET_TYPES:
                raise ValueError(
                    f"Invalid widget type '{w.get('type')}'. "
                    f"Must be one of: {sorted(VALID_WIDGET_TYPES)}"
                )

        dashboard = Dashboard(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            tenant_id=tenant_id,
            widgets=widgets,
            layout=data.get("layout", {}),
            permissions=data.get("permissions", {"roles": ["*"], "view_mode": "read"}),
            metadata={
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **data.get("metadata", {}),
            },
        )
        self._dashboards[dashboard.id] = dashboard
        logger.info("Created dashboard: %s (%s) widgets=%d tenant=%s",
                     dashboard.id, dashboard.code, dashboard.widget_count, tenant_id)
        return dashboard

    def get(self, dashboard_id: str) -> Optional[Dashboard]:
        return self._dashboards.get(dashboard_id)

    def list_by_tenant(self, tenant_id: str) -> list[Dashboard]:
        return [d for d in self._dashboards.values() if d.tenant_id == tenant_id]

    def add_widget(self, dashboard_id: str, widget: dict[str, Any]) -> Optional[Dashboard]:
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        if widget.get("type") not in VALID_WIDGET_TYPES:
            raise ValueError(f"Invalid widget type: {widget.get('type')}")
        widget.setdefault("id", str(uuid.uuid4()))
        dashboard.widgets.append(widget)
        return dashboard

    def remove_widget(self, dashboard_id: str, widget_id: str) -> Optional[Dashboard]:
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        dashboard.widgets = [w for w in dashboard.widgets if w.get("id") != widget_id]
        return dashboard

    def update(self, dashboard_id: str, updates: dict[str, Any]) -> Optional[Dashboard]:
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        for key, value in updates.items():
            if hasattr(dashboard, key) and key not in ("metadata",):
                setattr(dashboard, key, value)
            elif key == "metadata":
                dashboard.metadata.update(value)
        return dashboard

    def delete(self, dashboard_id: str) -> bool:
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False

    def get_visible_widgets(self, dashboard_id: str, user_roles: list[str]) -> list[dict[str, Any]]:
        """Get widgets filtered by user roles (simulates RBAC visibility)."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return []
        visible = []
        for w in dashboard.widgets:
            roles = w.get("visibility", {}).get("roles", ["*"])
            if "*" in roles or any(r in roles for r in user_roles):
                visible.append(w)
        return visible
