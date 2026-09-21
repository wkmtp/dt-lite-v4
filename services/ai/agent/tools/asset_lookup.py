"""AssetLookupTool — wraps the Core API for agent access.

Enables the agent to look up assets, entities, and their properties
through the Gateway, with automatic tenant scoping.

Supports:
- Direct lookup by asset_id or entity_id
- Keyword search across assets
- Hierarchical tree traversal (parent/child relationships)
- Property and capability retrieval
- Relationship graph navigation
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class AssetProperty(BaseModel):
    """A single property of an asset."""
    code: str = Field(..., description="Property code/identifier")
    name: str = Field(..., description="Human-readable name")
    value: Any = Field(None, description="Current value")
    data_type: str = Field("string", description="Data type")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    last_updated: Optional[str] = Field(None, description="ISO-8601 timestamp")


class AssetCapability(BaseModel):
    """A capability of an asset."""
    code: str = Field(..., description="Capability code")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Capability description")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AssetRelationship(BaseModel):
    """A relationship between assets."""
    relationship_id: str = Field(..., description="Relationship UUID")
    relationship_type: str = Field(..., description="Type of relationship")
    source_asset_id: str = Field(..., description="Source asset ID")
    target_asset_id: str = Field(..., description="Target asset ID")
    properties: dict[str, Any] = Field(default_factory=dict)


class Asset(BaseModel):
    """An asset in the DT-Lite system."""
    asset_id: str = Field(..., description="Asset UUID")
    entity_id: Optional[str] = Field(None, description="Associated entity UUID")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type code")
    description: Optional[str] = Field(None, description="Asset description")
    properties: list[AssetProperty] = Field(default_factory=list)
    capabilities: list[AssetCapability] = Field(default_factory=list)
    relationships: list[AssetRelationship] = Field(default_factory=list)
    parent_id: Optional[str] = Field(None, description="Parent asset ID (hierarchy)")
    children_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AssetLookupResult(BaseModel):
    """Result of an asset lookup operation."""
    success: bool = Field(True, description="Whether the lookup succeeded")
    asset: Optional[Asset] = Field(None, description="The found asset")
    assets: list[Asset] = Field(default_factory=list, description="Search results")
    total_count: int = Field(0, description="Total matching assets")
    search_query: Optional[str] = Field(None, description="The search query used")
    tree_depth: int = Field(0, description="Tree traversal depth")
    error: Optional[str] = Field(None, description="Error message if any")


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class AssetLookupTool:
    """Look up DT-Lite assets and their properties via the Core API.

    Tool name: ``asset_lookup``

    Input schema::

        {
            "asset_id": "<uuid>",
            "entity_id": "<uuid>",
            "search": "keyword",
            "asset_type": "temperature_sensor",
            "include_properties": true,
            "include_capabilities": true,
            "include_relationships": true,
            "include_children": false,
            "tree_depth": 1,
            "limit": 20
        }
    """

    tool_name = "asset_lookup"
    description = (
        "Look up DT-Lite assets, entities, and their semantic properties. "
        "Supports lookup by ID (asset_id or entity_id), keyword search, "
        "and hierarchical tree traversal. Returns asset properties, "
        "capabilities, and relationships. All results are scoped to the "
        "current tenant."
    )

    def __init__(self, tenant_id: str, config: Optional[AIConfig] = None) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()
        self._client = httpx.AsyncClient(
            base_url=self.config.GATEWAY_URL,
            timeout=30.0,
        )
        # Cache for tree traversal to avoid circular references
        self._visited_assets: set[str] = set()

    async def execute(
        self,
        tenant_id: str,
        asset_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        search: Optional[str] = None,
        asset_type: Optional[str] = None,
        include_properties: bool = True,
        include_capabilities: bool = True,
        include_relationships: bool = True,
        include_children: bool = False,
        tree_depth: int = 1,
        limit: int = 20,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an asset lookup.

        Args:
            tenant_id: Caller's tenant (validated against self.tenant_id).
            asset_id: Optional asset UUID for direct lookup.
            entity_id: Optional entity UUID for direct lookup.
            search: Optional keyword search string.
            asset_type: Optional asset type filter.
            include_properties: Whether to include asset properties (default True).
            include_capabilities: Whether to include capabilities (default True).
            include_relationships: Whether to include relationships (default True).
            include_children: Whether to traverse child assets (default False).
            tree_depth: Maximum depth for tree traversal (default 1).
            limit: Max search results (default 20).
            **kwargs: Ignored extra parameters.

        Returns:
            Dict with asset data, search results, or an error.
        """
        # Tenant validation
        if tenant_id != self.tenant_id:
            return {
                "success": False,
                "error": "tenant_mismatch",
                "message": "Access denied: tenant ID mismatch",
            }

        # Reset visited set for new lookup
        self._visited_assets.clear()

        try:
            if asset_id:
                # Direct lookup by asset ID
                result = await self._lookup_by_asset_id(
                    asset_id=asset_id,
                    include_properties=include_properties,
                    include_capabilities=include_capabilities,
                    include_relationships=include_relationships,
                    include_children=include_children,
                    tree_depth=tree_depth,
                )
                return result.model_dump()

            elif entity_id:
                # Lookup by entity ID
                result = await self._lookup_by_entity_id(
                    entity_id=entity_id,
                    include_properties=include_properties,
                    include_capabilities=include_capabilities,
                    include_relationships=include_relationships,
                )
                return result.model_dump()

            elif search:
                # Search by keyword
                result = await self._search_assets(
                    search=search,
                    asset_type=asset_type,
                    limit=limit,
                    include_properties=include_properties,
                    include_capabilities=include_capabilities,
                )
                return result.model_dump()

            else:
                return AssetLookupResult(
                    success=False,
                    error="missing_parameters",
                ).model_dump()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_detail = exc.response.text if exc.response.text else str(exc)

            if status_code == 404:
                logger.warning("Asset lookup 404: %s", error_detail)
                return AssetLookupResult(
                    success=False,
                    error="not_found",
                    message=f"Asset not found: {error_detail}",
                ).model_dump()
            elif status_code == 400:
                logger.warning("Asset lookup 400: %s", error_detail)
                return AssetLookupResult(
                    success=False,
                    error="bad_request",
                    message=f"Invalid asset lookup request: {error_detail}",
                ).model_dump()
            elif status_code == 500:
                logger.error("Asset lookup 500: %s", error_detail)
                return AssetLookupResult(
                    success=False,
                    error="internal_error",
                    message="Asset service internal error",
                ).model_dump()
            else:
                logger.warning("Asset lookup HTTP error %d: %s", status_code, error_detail)
                return AssetLookupResult(
                    success=False,
                    error=f"http_{status_code}",
                    message=f"Asset lookup failed with status {status_code}",
                ).model_dump()
        except httpx.TimeoutException:
            logger.error("Asset lookup timeout after 30s")
            return AssetLookupResult(
                success=False,
                error="timeout",
                message="Asset lookup timed out after 30 seconds",
            ).model_dump()
        except httpx.ConnectError as exc:
            logger.error("Asset lookup connection error: %s", exc)
            return AssetLookupResult(
                success=False,
                error="connection_error",
                message=f"Failed to connect to asset service: {exc}",
            ).model_dump()
        except Exception as exc:
            logger.error("Asset lookup unexpected error: %s", exc, exc_info=True)
            return AssetLookupResult(
                success=False,
                error="unexpected_error",
                message=f"Unexpected error during asset lookup: {exc}",
            ).model_dump()

    async def _lookup_by_asset_id(
        self,
        asset_id: str,
        include_properties: bool,
        include_capabilities: bool,
        include_relationships: bool,
        include_children: bool,
        tree_depth: int,
    ) -> AssetLookupResult:
        """Look up a single asset by ID with optional tree traversal."""
        try:
            resp = await self._client.get(
                f"/api/v1/assets/{asset_id}",
                headers={"X-Tenant-ID": self.tenant_id},
                params={
                    "include_properties": str(include_properties).lower(),
                    "include_capabilities": str(include_capabilities).lower(),
                    "include_relationships": str(include_relationships).lower(),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            asset = self._parse_asset(data.get("data", data))
            if include_children and tree_depth > 0:
                await self._traverse_children(asset, depth=tree_depth)

            return AssetLookupResult(success=True, asset=asset)

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return AssetLookupResult(
                    success=False,
                    error="asset_not_found",
                    message=f"Asset {asset_id} not found",
                )
            raise

    async def _lookup_by_entity_id(
        self,
        entity_id: str,
        include_properties: bool,
        include_capabilities: bool,
        include_relationships: bool,
    ) -> AssetLookupResult:
        """Look up an asset by entity ID."""
        try:
            resp = await self._client.get(
                f"/api/v1/entities/{entity_id}",
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()

            entity_data = data.get("data", data)
            asset_id = entity_data.get("asset_id") or entity_data.get("id")

            if asset_id:
                asset_resp = await self._client.get(
                    f"/api/v1/assets/{asset_id}",
                    headers={"X-Tenant-ID": self.tenant_id},
                    params={
                        "include_properties": str(include_properties).lower(),
                        "include_capabilities": str(include_capabilities).lower(),
                        "include_relationships": str(include_relationships).lower(),
                    },
                )
                asset_resp.raise_for_status()
                asset_data = asset_resp.json().get("data", asset_resp.json())
                asset = self._parse_asset(asset_data)
                return AssetLookupResult(success=True, asset=asset)
            else:
                return AssetLookupResult(
                    success=False,
                    error="no_asset_for_entity",
                    message=f"No asset found for entity {entity_id}",
                )

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return AssetLookupResult(
                    success=False,
                    error="entity_not_found",
                    message=f"Entity {entity_id} not found",
                )
            raise

    async def _search_assets(
        self,
        search: str,
        asset_type: Optional[str],
        limit: int,
        include_properties: bool,
        include_capabilities: bool,
    ) -> AssetLookupResult:
        """Search assets by keyword."""
        try:
            params: dict[str, Any] = {
                "q": search,
                "limit": limit,
                "include_properties": str(include_properties).lower(),
                "include_capabilities": str(include_capabilities).lower(),
            }
            if asset_type:
                params["asset_type"] = asset_type

            resp = await self._client.get(
                "/api/v1/assets/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()

            assets_data = data.get("data", data.get("results", []))
            total = data.get("total", data.get("count", len(assets_data)))

            assets = [self._parse_asset(a) for a in assets_data[:limit]]

            return AssetLookupResult(
                success=True,
                assets=assets,
                total_count=total,
                search_query=search,
            )

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                return AssetLookupResult(
                    success=False,
                    error="search_failed",
                    message=f"Asset search failed: {exc.response.text}",
                )
            raise

    async def _traverse_children(
        self,
        asset: Asset,
        depth: int,
        current_depth: int = 0,
    ) -> None:
        """Recursively traverse child assets up to tree_depth."""
        if depth <= 0 or current_depth >= depth:
            return

        if asset.asset_id in self._visited_assets:
            return
        self._visited_assets.add(asset.asset_id)

        if not asset.children_ids:
            return

        try:
            child_ids = asset.children_ids[:10]  # Limit for performance
            for child_id in child_ids:
                if child_id in self._visited_assets:
                    continue
                try:
                    resp = await self._client.get(
                        f"/api/v1/assets/{child_id}",
                        headers={"X-Tenant-ID": self.tenant_id},
                        params={
                            "include_properties": "true",
                            "include_relationships": "true",
                        },
                    )
                    resp.raise_for_status()
                    child_data = resp.json().get("data", resp.json())
                    child_asset = self._parse_asset(child_data)
                    asset.children_ids.append(child_id)
                    await self._traverse_children(child_asset, depth, current_depth + 1)
                except httpx.HTTPStatusError:
                    logger.warning(
                        "Failed to load child asset %s for parent %s",
                        child_id, asset.asset_id,
                    )
        except Exception as exc:
            logger.error(
                "Error traversing children for asset %s: %s",
                asset.asset_id, exc, exc_info=True,
            )

    def _parse_asset(self, data: dict[str, Any]) -> Asset:
        """Parse asset data from API response."""
        properties = []
        for prop in data.get("properties", []):
            properties.append(AssetProperty(
                code=prop.get("code", prop.get("property_code", "")),
                name=prop.get("name", prop.get("property_name", "")),
                value=prop.get("value"),
                data_type=prop.get("data_type", "string"),
                unit=prop.get("unit"),
                last_updated=prop.get("last_updated", prop.get("updated_at")),
            ))

        capabilities = []
        for cap in data.get("capabilities", []):
            capabilities.append(AssetCapability(
                code=cap.get("code", cap.get("capability_code", "")),
                name=cap.get("name", cap.get("capability_name", "")),
                description=cap.get("description", ""),
                input_schema=cap.get("input_schema", {}),
                output_schema=cap.get("output_schema", {}),
            ))

        relationships = []
        for rel in data.get("relationships", []):
            relationships.append(AssetRelationship(
                relationship_id=rel.get("id", rel.get("relationship_id", "")),
                relationship_type=rel.get("type", rel.get("relationship_type", "")),
                source_asset_id=rel.get("source_id", rel.get("source_asset_id", "")),
                target_asset_id=rel.get("target_id", rel.get("target_asset_id", "")),
                properties=rel.get("properties", {}),
            ))

        return Asset(
            asset_id=data.get("id", data.get("asset_id", "")),
            entity_id=data.get("entity_id"),
            name=data.get("name", data.get("asset_name", "")),
            asset_type=data.get("type", data.get("asset_type", "")),
            description=data.get("description"),
            properties=properties,
            capabilities=capabilities,
            relationships=relationships,
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def get_asset_hierarchy(
        self,
        tenant_id: str,
        root_asset_id: str,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Get the full asset hierarchy tree starting from root_asset_id.

        Args:
            tenant_id: Caller's tenant.
            root_asset_id: Root asset UUID.
            max_depth: Maximum tree depth to traverse.

        Returns:
            Dict with hierarchical asset tree.
        """
        if tenant_id != self.tenant_id:
            return {"success": False, "error": "tenant_mismatch"}

        self._visited_assets.clear()
        try:
            resp = await self._client.get(
                f"/api/v1/assets/{root_asset_id}/tree",
                headers={"X-Tenant-ID": self.tenant_id},
                params={"max_depth": max_depth},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data.get("data", data)}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"success": False, "error": "asset_not_found"}
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("Asset hierarchy error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AssetLookupTool":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
