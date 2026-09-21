"""MQTT Mapping — Topic to DataPoint resolution."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MQTTMapping:
    """Resolves DataPoint.extra_data to MQTT topic patterns."""

    @staticmethod
    def parse(extra_data: dict) -> Optional[dict]:
        if not extra_data or "mqtt" not in extra_data:
            return None
        mqtt = extra_data["mqtt"]
        if "topic" not in mqtt:
            return None
        return {
            "topic": mqtt["topic"],
            "qos": mqtt.get("qos", 1),
            "payload_format": mqtt.get("payload_format", "json"),
            "retained": mqtt.get("retained", False),
        }

    @staticmethod
    def parse_external_id(external_id: str) -> Optional[str]:
        try:
            parts = external_id.split(":", 1)
            if len(parts) == 2 and parts[0] == "mqtt":
                return parts[1]
        except (ValueError, IndexError):
            pass
        return None
