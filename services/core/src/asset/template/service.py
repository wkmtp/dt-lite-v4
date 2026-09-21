"""Asset Template Service — Versioning, instantiation, parameter binding."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from services.core.src.asset.service import Asset

logger = logging.getLogger(__name__)


@dataclass
class AssetTemplate:
    """Asset template matching Universal Contract v1.0."""
    id: str
    code: str
    name: str
    version: str  # SemVer: major.minor.patch
    asset_schema: dict[str, Any]  # JSON Schema reference
    point_templates: list[dict[str, Any]] = field(default_factory=list)
    capability_templates: list[dict[str, Any]] = field(default_factory=list)
    relationship_templates: list[dict[str, Any]] = field(default_factory=list)
    instantiation_params_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class AssetTemplateService:
    """
    Asset Template Service: versioning, instantiation with parameter binding.
    NO asset CRUD, NO composition logic.
    """

    def __init__(self) -> None:
        self._templates: dict[str, AssetTemplate] = {}

    def register(self, template: AssetTemplate) -> None:
        """Register a template version."""
        self._templates[template.id] = template
        logger.info("Registered template: %s v%s", template.code, template.version)

    def get(self, template_id: str) -> Optional[AssetTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def list_by_code(self, code: str) -> list[AssetTemplate]:
        """List all versions of a template."""
        return [t for t in self._templates.values() if t.code == code]

    def instantiate(self, template_id: str, params: dict[str, Any], tenant_id: str) -> Asset:
        """
        Instantiate an asset from a template with parameter binding.
        Validates params against instantiation_params_schema (basic check).
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Basic parameter validation
        required_params = template.instantiation_params_schema.get("required", [])
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required instantiation param: {param}")

        # Build asset from template
        asset_data = {
            "id": f"asset-{template_id}-{params.get('instance_id', '001')}",
            "code": template.code,
            "name": params.get("name", template.name),
            "category": params.get("category", self._infer_category(template.code)),
            "attributes": params.get("attributes", {}),
            "capabilities": [c["code"] for c in template.capability_templates],
            "relationships": [r.get("type", "contains") for r in template.relationship_templates],
            "model_bindings": [],
            "metadata": {"tenant_id": tenant_id},
        }
        return Asset(**asset_data)

    def _infer_category(self, code: str) -> str:
        """Infer category from template code."""
        parts = code.split(".")
        if len(parts) >= 3:
            domain_map = {
                "energy": "energy", "hvac": "facility", "water": "water",
                "security": "security", "fire": "fire", "elevator": "facility",
                "access": "security", "parking": "transport", "waste": "environment",
                "green": "environment", "it": "it", "production": "production",
                "transport": "transport", "lighting": "facility",
            }
            for key in domain_map:
                if key in parts:
                    return domain_map[key]
        return "facility"
