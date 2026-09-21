"""CapabilityPlugin module — Abstract base, protocol-specific implementations."""
from services.core.src.capability.plugin.base import (
    CapabilityPlugin, PluginResult,
    BACnetCapabilityPlugin, ModbusCapabilityPlugin,
    OPCUACapabilityPlugin, MQTTCapabilityPlugin,
    CapabilityPluginRegistry,
)

__all__ = [
    "CapabilityPlugin", "PluginResult",
    "BACnetCapabilityPlugin", "ModbusCapabilityPlugin",
    "OPCUACapabilityPlugin", "MQTTCapabilityPlugin",
    "CapabilityPluginRegistry",
]
