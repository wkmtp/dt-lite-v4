"""CapabilityPlugin Framework — Abstract base, protocol-specific implementations."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginResult:
    """Result of a capability plugin execution."""
    success: bool
    output: dict[str, Any]
    latency_ms: float
    error: Optional[str] = None


class CapabilityPlugin(ABC):
    """
    Abstract base class for capability plugins.
    Defines HOW a capability is executed (protocol-specific).
    """

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> PluginResult:
        """Execute the capability. Returns result with output."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check plugin health status."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources."""
        pass


class BACnetCapabilityPlugin(CapabilityPlugin):
    """BACnet protocol-specific capability plugin."""

    def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._connected = False

    def execute(self, input_data: dict[str, Any]) -> PluginResult:
        # In production: use bacpypes3 for BACnet read/write
        return PluginResult(success=True, output={"value": input_data.get("value", 0)}, latency_ms=5.0)

    def health_check(self) -> bool:
        return self._connected

    def shutdown(self) -> None:
        self._connected = False


class ModbusCapabilityPlugin(CapabilityPlugin):
    """Modbus protocol-specific capability plugin."""

    def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._connected = False

    def execute(self, input_data: dict[str, Any]) -> PluginResult:
        # In production: use pymodbus for Modbus read/write
        return PluginResult(success=True, output={"value": input_data.get("value", 0)}, latency_ms=8.0)

    def health_check(self) -> bool:
        return self._connected

    def shutdown(self) -> None:
        self._connected = False


class OPCUACapabilityPlugin(CapabilityPlugin):
    """OPC UA protocol-specific capability plugin."""

    def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._connected = False

    def execute(self, input_data: dict[str, Any]) -> PluginResult:
        # In production: use asyncua for OPC UA read/write
        return PluginResult(success=True, output={"value": input_data.get("value", 0)}, latency_ms=10.0)

    def health_check(self) -> bool:
        return self._connected

    def shutdown(self) -> None:
        self._connected = False


class MQTTCapabilityPlugin(CapabilityPlugin):
    """MQTT protocol-specific capability plugin."""

    def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._connected = False

    def execute(self, input_data: dict[str, Any]) -> PluginResult:
        # In production: use paho-mqtt for MQTT publish/subscribe
        return PluginResult(success=True, output={"value": input_data.get("value", 0)}, latency_ms=3.0)

    def health_check(self) -> bool:
        return self._connected

    def shutdown(self) -> None:
        self._connected = False


class CapabilityPluginRegistry:
    """Registry for capability plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, CapabilityPlugin] = {}
        self._versions: dict[str, str] = {}

    def register(self, code: str, plugin: CapabilityPlugin, version: str = "1.0.0") -> None:
        """Register a capability plugin."""
        self._plugins[code] = plugin
        self._versions[code] = version
        logger.info("Registered plugin: %s v%s", code, version)

    def get(self, code: str) -> Optional[CapabilityPlugin]:
        """Get plugin by code."""
        return self._plugins.get(code)

    def list_plugins(self) -> dict[str, str]:
        """List all registered plugins with versions."""
        return dict(self._versions)
