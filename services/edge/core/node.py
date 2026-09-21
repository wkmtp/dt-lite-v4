"""Edge Runtime Core — EdgeNode lifecycle management."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ComponentHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ResourceUsage:
    """Current resource usage of the edge node."""
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    disk_bytes: int = 0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceQuota:
    """Resource quota configuration for the edge node."""
    cpu_limit: float = 2.0
    memory_limit_bytes: int = 2 * 1024 * 1024 * 1024  # 2Gi
    disk_limit_bytes: int = 10 * 1024 * 1024 * 1024  # 10Gi
    max_connections: int = 100
    max_models: int = 5


class EdgeNode:
    """
    Core Edge Node lifecycle manager.

    Handles:
    - Provisioning and registration
    - Heartbeat reporting
    - Resource monitoring
    - Health checks
    - Configuration management
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        cloud_url: str = "ws://localhost:8000",
        provisioning_token: Optional[str] = None,
    ) -> None:
        self.node_id = node_id or str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.cloud_url = cloud_url
        self.provisioning_token = provisioning_token
        self.status = NodeStatus.PROVISIONING
        self.health: dict[str, ComponentHealth] = {}
        self.resource_usage = ResourceUsage()
        self.resource_quota = ResourceQuota()
        self.config: dict[str, Any] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._monitored_components: list[str] = []

    async def provision(self, token: str) -> dict[str, Any]:
        """
        Provision the edge node with a token.
        Returns node configuration and metadata.
        """
        # Validate token (would call cloud API in production)
        if not token or len(token) < 8:
            raise ValueError("Invalid provisioning token")

        self.provisioning_token = token
        self.status = NodeStatus.RUNNING

        # Generate node configuration
        config = {
            "node_id": self.node_id,
            "tenant_id": self.tenant_id,
            "cloud_url": self.cloud_url,
            "heartbeat_interval_ms": 30000,
            "sync_enabled": True,
            "local_storage_enabled": True,
            "inference_enabled": True,
        }
        self.config = config
        logger.info("Edge node provisioned: %s", self.node_id)
        return config

    async def heartbeat(self) -> dict[str, Any]:
        """
        Send heartbeat to cloud.
        Returns acknowledgment with potential config updates.
        """
        heartbeat_data = {
            "node_id": self.node_id,
            "status": self.status.value,
            "resources": {
                "cpu_pct": self.resource_usage.cpu_percent,
                "memory_bytes": self.resource_usage.memory_bytes,
                "disk_bytes": self.resource_usage.disk_bytes,
            },
            "health": {k: v.value for k, v in self.health.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # In production: send to cloud via WebSocket
        logger.debug("Heartbeat sent: %s", json.dumps(heartbeat_data))
        return {
            "ack": True,
            "next_heartbeat_ms": 30000,
            "config_version": "1.0",
        }

    async def start_heartbeat_loop(self, interval_ms: int = 30000) -> None:
        """Start periodic heartbeat."""
        async def _heartbeat_loop() -> None:
            while self.status in (NodeStatus.RUNNING, NodeStatus.DEGRADED):
                try:
                    await self.heartbeat()
                except Exception as exc:
                    logger.error("Heartbeat failed: %s", exc)
                await asyncio.sleep(interval_ms / 1000)

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())

    async def stop(self) -> None:
        """Stop the edge node gracefully."""
        self.status = NodeStatus.STOPPING
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        self.status = NodeStatus.STOPPED
        logger.info("Edge node stopped: %s", self.node_id)

    def update_resource_usage(self, usage: ResourceUsage) -> None:
        """Update current resource usage."""
        self.resource_usage = usage

    def check_resource_quota(self) -> dict[str, Any]:
        """Check if resource usage is within quota."""
        memory_pct = (
            self.resource_usage.memory_bytes / self.resource_quota.memory_limit_bytes
            if self.resource_quota.memory_limit_bytes > 0
            else 0.0
        )
        disk_pct = (
            self.resource_usage.disk_bytes / self.resource_quota.disk_limit_bytes
            if self.resource_quota.disk_limit_bytes > 0
            else 0.0
        )
        return {
            "cpu_ok": self.resource_usage.cpu_percent <= self.resource_quota.cpu_limit * 100,
            "memory_ok": memory_pct <= 0.9,
            "disk_ok": disk_pct <= 0.9,
            "memory_pct": memory_pct,
            "disk_pct": disk_pct,
        }

    def get_health_summary(self) -> dict[str, Any]:
        """Get health summary of all components."""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "components": {k: v.value for k, v in self.health.items()},
            "resources": {
                "cpu_pct": self.resource_usage.cpu_percent,
                "memory_bytes": self.resource_usage.memory_bytes,
                "disk_bytes": self.resource_usage.disk_bytes,
            },
        }


# Pydantic schemas for API
class ProvisionRequest(BaseModel):
    token: str = Field(..., min_length=8)
    node_id: Optional[str] = None
    tenant_id: Optional[str] = None


class ProvisionResponse(BaseModel):
    node_id: str
    config: dict[str, Any]
    expires_at: Optional[str] = None


class HeartbeatRequest(BaseModel):
    node_id: str
    status: str = "running"
    resources: dict[str, Any] = Field(default_factory=dict)


class HeartbeatResponse(BaseModel):
    ack: bool
    next_heartbeat_ms: int = 30000
    config_version: str = "1.0"


class HealthResponse(BaseModel):
    status: str = "ok"
    uptime_s: float = 0.0
    components: dict[str, str] = Field(default_factory=dict)
    version: str = "4.18.0"
