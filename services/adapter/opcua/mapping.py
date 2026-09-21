"""OPC-UA Mapping — NodeId to DataPoint resolution."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OPCUAMapping:
    """Resolves DataPoint.extra_data to OPC-UA NodeId."""

    @staticmethod
    def parse(extra_data: dict) -> Optional[dict]:
        if not extra_data or "opcua" not in extra_data:
            return None
        opcua = extra_data["opcua"]
        if "node_id" not in opcua:
            return None
        return {
            "node_id": opcua["node_id"],
            "namespace": opcua.get("namespace", "0"),
            "attribute": opcua.get("attribute", "Value"),
            "data_type": opcua.get("data_type", "Float"),
        }

    @staticmethod
    def parse_external_id(external_id: str) -> Optional[str]:
        try:
            parts = external_id.split(":", 2)
            if len(parts) >= 3 and parts[0] == "opcua":
                return f"{parts[1]}:{parts[2]}"
        except (ValueError, IndexError):
            pass
        return None
