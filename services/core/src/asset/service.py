"""Asset Service — CRUD, lifecycle, validation, search."""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Frozen naming convention regex
ASSET_CODE_PATTERN = re.compile(
    r"^asset\.(park|factory)\."
    r"(energy|hvac|water|security|transport|environment|production|"
    r"lighting|fire|elevator|access|parking|waste|green|it|facility|spatial)\."
    r"[a-z_][a-z0-9_]*$"
)

LIFECYCLE_STATUSES = {"provisioned", "active", "decommissioned", "retired"}


@dataclass
class Asset:
    """Asset entity matching Universal Contract v1.0."""
    id: str
    code: str
    name: str
    category: str
    attributes: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    model_bindings: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def lifecycle_status(self) -> str:
        return self.metadata.get("lifecycle", {}).get("status", "provisioned")

    def activate(self) -> None:
        self.metadata.setdefault("lifecycle", {})["status"] = "active"

    def decommission(self) -> None:
        self.metadata.setdefault("lifecycle", {})["status"] = "decommissioned"

    def retire(self) -> None:
        self.metadata.setdefault("lifecycle", {})["status"] = "retired"


class AssetService:
    """
    Asset Service: CRUD, lifecycle management, validation, search.
    NO template logic, NO composition logic, NO relationship logic.
    """

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def create(self, data: dict[str, Any], tenant_id: str) -> Asset:
        """Create asset with validation."""
        # Validate required fields
        for key in ["id", "code", "name", "category"]:
            if key not in data:
                raise ValueError(f"Asset missing required field: {key}")

        # Validate naming convention
        if not ASSET_CODE_PATTERN.match(data["code"]):
            raise ValueError(
                f"Asset code '{data['code']}' does not match naming convention: "
                f"asset.<domain>.<sub_domain>.<type>"
            )

        # Validate category
        valid_categories = {
            "building", "facility", "energy", "water", "security",
            "transport", "environment", "production", "fire", "elevator",
            "access", "parking", "waste", "green", "it",
        }
        if data["category"] not in valid_categories:
            raise ValueError(f"Invalid category: {data['category']}")

        asset = Asset(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            category=data["category"],
            attributes=data.get("attributes", {}),
            capabilities=data.get("capabilities", []),
            relationships=data.get("relationships", []),
            model_bindings=data.get("model_bindings", []),
            metadata={
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "lifecycle": {"status": "provisioned"},
                **data.get("metadata", {}),
            },
        )
        self._assets[asset.id] = asset
        logger.info("Created asset: %s (%s)", asset.id, asset.code)
        return asset

    def get(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        return self._assets.get(asset_id)

    def list_by_code_prefix(self, prefix: str, tenant_id: str) -> list[Asset]:
        """Search assets by code prefix."""
        return [
            a for a in self._assets.values()
            if a.code.startswith(prefix) and a.metadata.get("tenant_id") == tenant_id
        ]

    def list_by_category(self, category: str, tenant_id: str) -> list[Asset]:
        """Search assets by category."""
        return [
            a for a in self._assets.values()
            if a.category == category and a.metadata.get("tenant_id") == tenant_id
        ]

    def all(self, tenant_id: str) -> list[Asset]:
        """List all assets for a tenant."""
        return [a for a in self._assets.values() if a.metadata.get("tenant_id") == tenant_id]

    def update(self, asset_id: str, updates: dict[str, Any]) -> Optional[Asset]:
        """Update asset fields."""
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        for key, value in updates.items():
            if hasattr(asset, key) and key not in ("metadata", "lifecycle_status"):
                setattr(asset, key, value)
            elif key == "metadata":
                asset.metadata.update(value)
        return asset

    def delete(self, asset_id: str) -> bool:
        """Soft delete: set lifecycle to retired."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        asset.retire()
        logger.info("Retired asset: %s", asset_id)
        return True
