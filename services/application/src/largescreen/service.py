"""LargeScreen Service — Read-only, auto-rotate, kiosk-mode displays.

Separate from Dashboard (SL-09 / AG-P0-07):
  - LargeScreen: read-only, single-layout, auto-rotate playlist, kiosk-mode
  - Dashboard: interactive, multi-user, drill-down, real-time WebSocket
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

LARGESCREEN_CODE_PATTERN = re.compile(r"^ls\.(park|factory)\.[a-z_][a-z0-9_]*$")


@dataclass
class LayoutSlot:
    """A position in a large screen layout."""
    id: str
    widget_type: str
    content: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(default_factory=dict)


@dataclass
class PlaylistItem:
    """An item in the auto-rotate playlist."""
    layout_id: str
    duration_seconds: int = 30


@dataclass
class LargeScreen:
    """LargeScreen entity — read-only, auto-rotate, kiosk."""
    id: str
    code: str
    name: str
    tenant_id: str
    layouts: list[dict[str, Any]] = field(default_factory=list)
    playlist: list[dict[str, Any]] = field(default_factory=list)
    rotation_interval_seconds: int = 30
    kiosk_mode: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def layout_count(self) -> int:
        return len(self.layouts)

    @property
    def playlist_count(self) -> int:
        return len(self.playlist)

    @property
    def created_at(self) -> str:
        return self.metadata.get("created_at", "")


class LargeScreenService:
    """LargeScreen service: CRUD, layout management, auto-rotate playlist.

    NO interactive widgets (DashboardService), NO user permissions.
    LargeScreen is purely read-only broadcast.
    """

    def __init__(self) -> None:
        self._screens: dict[str, LargeScreen] = {}

    def create(self, data: dict[str, Any], tenant_id: str) -> LargeScreen:
        """Create a LargeScreen with validation."""
        for key in ["id", "code", "name"]:
            if key not in data:
                raise ValueError(f"LargeScreen missing required field: {key}")

        if not LARGESCREEN_CODE_PATTERN.match(data["code"]):
            raise ValueError(
                f"LargeScreen code '{data['code']}' does not match convention: "
                f"ls.<domain>.<type>"
            )

        interval = data.get("rotation_interval_seconds", 30)
        if not isinstance(interval, int) or interval < 5:
            raise ValueError("rotation_interval_seconds must be an integer >= 5")

        screen = LargeScreen(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            tenant_id=tenant_id,
            layouts=data.get("layouts", []),
            playlist=data.get("playlist", []),
            rotation_interval_seconds=interval,
            kiosk_mode=data.get("kiosk_mode", True),
            metadata={
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **data.get("metadata", {}),
            },
        )
        self._screens[screen.id] = screen
        logger.info("Created LargeScreen: %s (%s) layouts=%d tenant=%s",
                     screen.id, screen.code, screen.layout_count, tenant_id)
        return screen

    def get(self, screen_id: str) -> Optional[LargeScreen]:
        return self._screens.get(screen_id)

    def list_by_tenant(self, tenant_id: str) -> list[LargeScreen]:
        return [s for s in self._screens.values() if s.tenant_id == tenant_id]

    def add_layout(self, screen_id: str, layout: dict[str, Any]) -> Optional[LargeScreen]:
        screen = self._screens.get(screen_id)
        if not screen:
            return None
        layout.setdefault("id", str(uuid.uuid4()))
        screen.layouts.append(layout)
        # Auto-add to playlist if not already present
        if not any(p.get("layout_id") == layout["id"] for p in screen.playlist):
            screen.playlist.append({
                "layout_id": layout["id"],
                "duration_seconds": screen.rotation_interval_seconds,
            })
        return screen

    def remove_layout(self, screen_id: str, layout_id: str) -> Optional[LargeScreen]:
        screen = self._screens.get(screen_id)
        if not screen:
            return None
        screen.layouts = [l for l in screen.layouts if l.get("id") != layout_id]
        screen.playlist = [p for p in screen.playlist if p.get("layout_id") != layout_id]
        return screen

    def update(self, screen_id: str, updates: dict[str, Any]) -> Optional[LargeScreen]:
        screen = self._screens.get(screen_id)
        if not screen:
            return None
        for key, value in updates.items():
            if hasattr(screen, key) and key not in ("metadata",):
                setattr(screen, key, value)
            elif key == "metadata":
                screen.metadata.update(value)
        return screen

    def delete(self, screen_id: str) -> bool:
        if screen_id in self._screens:
            del self._screens[screen_id]
            return True
        return False

    def current_layout(self, screen_id: str, index: int = 0) -> Optional[dict[str, Any]]:
        """Get the layout at the given playlist index (for rotation simulation)."""
        screen = self._screens.get(screen_id)
        if not screen or not screen.playlist:
            return None
        idx = index % len(screen.playlist)
        playlist_item = screen.playlist[idx]
        layout_id = playlist_item.get("layout_id")
        for layout in screen.layouts:
            if layout.get("id") == layout_id:
                return layout
        return None
