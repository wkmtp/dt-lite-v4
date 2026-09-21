"""Adapter matching engine — Capability-to-Adapter mapping (ADR-008)."""
import logging
from typing import Optional

from services.adapter.models import CapabilityMatch

logger = logging.getLogger(__name__)

# Semantic tag compatibility matrix
SEMAPHORE_TAG_MAP: dict[str, list[str]] = {
    "temperature": ["bacnet", "modbus", "opcua"],
    "temperature_measurement": ["bacnet", "modbus", "opcua"],
    "thermal": ["bacnet", "modbus", "opcua"],
    "humidity": ["bacnet", "modbus", "opcua"],
    "humidity_measurement": ["bacnet", "modbus", "opcua"],
    "power": ["modbus", "opcua"],
    "energy": ["modbus", "opcua"],
    "voltage": ["modbus", "opcua"],
    "current": ["modbus", "opcua"],
    "power_measurement": ["modbus", "opcua"],
    "energy_measurement": ["modbus", "opcua"],
    "alarm": ["bacnet", "modbus", "opcua", "mqtt"],
    "status": ["bacnet", "modbus", "opcua", "mqtt"],
    "on_off": ["bacnet", "modbus", "opcua", "mqtt"],
    "position": ["modbus", "opcua"],
    "motion": ["modbus", "opcua"],
    "pressure": ["modbus", "bacnet", "opcua"],
}


class CapabilityAdapterMatcher:
    """Matches CapabilityDefinition to compatible Adapter types."""

    def __init__(self):
        self._tag_map = SEMAPHORE_TAG_MAP

    async def match(
        self,
        capability_key: str,
        data_type: str,
        unit: Optional[str] = None,
        semantic_tags: Optional[list[str]] = None,
        required_capabilities: Optional[list[str]] = None,
    ) -> list[CapabilityMatch]:
        candidates: list[CapabilityMatch] = []
        all_tags = set()

        if semantic_tags:
            all_tags.update(semantic_tags)
        all_tags.add(capability_key.lower())
        all_tags.add(capability_key.replace("_", "").lower())

        adapter_scores: dict[str, float] = {}
        for tag in all_tags:
            if tag in self._tag_map:
                for adapter_type in self._tag_map[tag]:
                    adapter_scores[adapter_type] = adapter_scores.get(adapter_type, 0) + 1

        for adapter_type, tag_score in adapter_scores.items():
            confidence = min(1.0, tag_score / max(len(all_tags), 1))
            dt_score = 0.1
            cap_score = 1.0
            required_caps = required_capabilities or []
            if required_caps:
                adapter_caps = self._get_adapter_capabilities(adapter_type)
                missing = [c for c in required_caps if c not in adapter_caps]
                if missing:
                    cap_score = max(0.0, 1.0 - len(missing) * 0.3)

            total_confidence = round(min(1.0, confidence * 0.6 + dt_score + cap_score * 0.4), 2)

            if total_confidence > 0:
                candidates.append(CapabilityMatch(
                    adapter_type=adapter_type,
                    confidence=total_confidence,
                    required_capabilities=required_caps,
                    notes=f"Matched via tags: {', '.join(list(all_tags)[:3])}",
                ))

        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates

    async def validate_adapter_supports_capability(self, adapter_type: str, capability_key: str, required_capabilities: list[str]) -> bool:
        matches = await self.match(capability_key=capability_key, data_type="FLOAT", required_capabilities=required_capabilities)
        return any(m.adapter_type == adapter_type and m.confidence > 0.3 for m in matches)

    def _get_adapter_capabilities(self, adapter_type: str) -> list:
        default_caps = {
            "bacnet": ["READ", "WRITE", "DISCOVERY", "SUBSCRIBE"],
            "modbus": ["READ", "WRITE", "DISCOVERY"],
            "mqtt": ["READ", "WRITE", "SUBSCRIBE"],
            "opcua": ["READ", "WRITE", "DISCOVERY", "SUBSCRIBE"],
        }
        return default_caps.get(adapter_type, ["READ", "WRITE"])
