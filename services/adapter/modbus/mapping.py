"""Modbus Mapping — DataPoint.extra_data to Modbus address resolution."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VALID_MODBUS_FC = {1, 2, 3, 4, 5, 6, 15, 16}
VALID_MODBUS_TYPES = {"bool", "uint16", "int16", "uint32", "int32", "float32", "float64"}
VALID_BYTE_ORDERS = {"big", "little", "swap"}


class ModbusMapping:
    """Resolves DataPoint.extra_data to Modbus register addresses."""

    @staticmethod
    def parse(extra_data: dict) -> Optional[dict]:
        if not extra_data or "modbus" not in extra_data:
            return None
        modbus = extra_data["modbus"]
        for field in ["function_code", "address"]:
            if field not in modbus:
                return None
        fc = modbus["function_code"]
        if fc not in VALID_MODBUS_FC:
            return None
        data_type = modbus.get("data_type", "uint16")
        if data_type not in VALID_MODBUS_TYPES:
            return None
        byte_order = modbus.get("byte_order", "big")
        if byte_order not in VALID_BYTE_ORDERS:
            return None
        return {
            "function_code": int(fc), "address": int(modbus["address"]),
            "data_type": data_type, "byte_order": byte_order,
            "scale": float(modbus.get("scale", 1.0)),
            "offset": float(modbus.get("offset", 0)),
            "unit_id": int(modbus.get("unit_id", 1)),
            "count": int(modbus.get("count", 1)),
        }

    @staticmethod
    def build_modbus_address(mapping: dict) -> str:
        return f"modbus:{mapping['function_code']}:{mapping['address']}:{mapping.get('count', 1)}:{mapping['data_type']}"

    @staticmethod
    def parse_external_id(external_id: str) -> Optional[dict]:
        try:
            parts = external_id.split(":")
            if len(parts) >= 4 and parts[0] == "modbus":
                return {
                    "function_code": int(parts[1]), "address": int(parts[2]),
                    "count": int(parts[3]) if len(parts) > 3 else 1,
                    "data_type": parts[4] if len(parts) > 4 else "uint16",
                }
        except (ValueError, IndexError):
            pass
        return None

    @staticmethod
    def convert_value(raw_value: int, data_type: str, scale: float, offset: float, byte_order: str = "big") -> float:
        return raw_value * scale + offset
