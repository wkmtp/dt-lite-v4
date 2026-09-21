"""BACnet Mapping — DataPoint.extra_data to BACnet address resolution."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VALID_BACNET_OBJECT_TYPES = {
    "analogInput", "analogOutput", "analogValue",
    "binaryInput", "binaryOutput", "binaryValue",
    "multistateInput", "multistateOutput", "multistateValue",
}

READABLE_PROPERTIES = {
    "presentValue", "statusFlags", "outOfService", "relinquishDefault",
    "description", "objectName", "objectIdentifier", "objectType",
}


class BACnetMapping:
    """Resolves DataPoint.extra_data to BACnet object addresses."""

    @staticmethod
    def parse(extra_data: dict) -> Optional[dict]:
        if not extra_data or "bacnet" not in extra_data:
            return None
        bacnet = extra_data["bacnet"]
        required = ["object_type", "object_instance", "property"]
        for field in required:
            if field not in bacnet:
                return None
        obj_type = bacnet["object_type"]
        if obj_type not in VALID_BACNET_OBJECT_TYPES:
            return None
        prop = bacnet["property"]
        if prop not in READABLE_PROPERTIES:
            return None
        return {
            "object_type": obj_type,
            "object_instance": int(bacnet["object_instance"]),
            "property": prop,
            "unit": bacnet.get("unit"),
            "quality": bacnet.get("quality", "GOOD"),
            "access": bacnet.get("access", "read"),
        }

    @staticmethod
    def build_bacnet_address(mapping: dict) -> str:
        return f"bacnet:{mapping['object_type']}:{mapping['object_instance']}:{mapping['property']}"

    @staticmethod
    def parse_external_id(external_id: str) -> Optional[dict]:
        try:
            parts = external_id.split(":")
            if len(parts) == 4 and parts[0] == "bacnet":
                return {
                    "object_type": parts[1],
                    "object_instance": int(parts[2]),
                    "property": parts[3],
                }
        except (ValueError, IndexError):
            pass
        return None
