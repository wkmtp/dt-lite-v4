"""Discovery Engine — Protocol-specific discovery (BACnet, Modbus, OPC UA)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Simulated discovery results for testing
SIMULATED_DISCOVERY = {
    "bacnet": [
        {"object_id": "ai-001", "name": "Analog Input 1", "type": "analog-input",
         "address": "bacnet:ai:100:presentValue", "data_type": "float32", "unit": "degC"},
        {"object_id": "bo-001", "name": "Binary Output 1", "type": "binary-output",
         "address": "bacnet:bo:200:outStatus", "data_type": "boolean", "unit": ""},
    ],
    "modbus": [
        {"object_id": "reg-100", "name": "Holding Register 100", "type": "holding-register",
         "address": "modbus:slave=1:fc=3:addr=100", "data_type": "int16", "unit": "kW"},
        {"object_id": "coil-001", "name": "Coil 1", "type": "coil",
         "address": "modbus:slave=1:fc=1:addr=0", "data_type": "boolean", "unit": ""},
    ],
    "opcua": [
        {"object_id": "node-2001", "name": "Temperature Node", "type": "analytical-item",
         "address": "opcua:ns=2:i=2001", "data_type": "float32", "unit": "degC"},
        {"object_id": "node-2002", "name": "Pressure Node", "type": "analytical-item",
         "address": "opcua:ns=2:i=2002", "data_type": "float32", "unit": "Pa"},
    ],
}


class DiscoveryEngine:
    """
    Discovery Engine: protocol-specific device/object discovery.
    Simulated for testing; production would use real protocol libraries.
    """

    def discover_bacnet(self, network: str = "255.255.255.255") -> list[dict[str, Any]]:
        """Simulate BACnet Who-Is/I-Am discovery."""
        return SIMULATED_DISCOVERY.get("bacnet", [])

    def discover_modbus(self, ip: str, start_reg: int = 0, count: int = 10) -> list[dict[str, Any]]:
        """Simulate Modbus register scan."""
        return SIMULATED_DISCOVERY.get("modbus", [])

    def discover_opcua(self, endpoint: str) -> list[dict[str, Any]]:
        """Simulate OPC UA namespace browse."""
        return SIMULATED_DISCOVERY.get("opcua", [])

    def discover(self, protocol: str, **kwargs) -> list[dict[str, Any]]:
        """Generic discovery dispatcher."""
        if protocol == "bacnet":
            return self.discover_bacnet(kwargs.get("network", "255.255.255.255"))
        elif protocol == "modbus":
            return self.discover_modbus(kwargs.get("ip", "192.168.1.1"))
        elif protocol == "opcua":
            return self.discover_opcua(kwargs.get("endpoint", "opc.tcp://localhost:4840"))
        else:
            raise ValueError(f"Unsupported protocol for discovery: {protocol}")
