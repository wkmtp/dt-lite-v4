"""OntologySearchTool — wraps the Ontology API for agent access.

Allows the agent to search the DT-Lite ontology for concepts,
entity types, capabilities, and semantic properties.
All queries are tenant-scoped.

Supports:
- Keyword search across ontology elements
- Semantic search via embedding fallback
- Category and type filtering
- Relationship traversal
- Structured result formatting
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

class OntologyConcept(BaseModel):
    """A concept in the ontology."""
    concept_id: str = Field(..., description="Concept UUID")
    name: str = Field(..., description="Concept name")
    description: str = Field(..., description="Concept description")
    category: str = Field(..., description="Concept category")
    parent_concept_id: Optional[str] = Field(None, description="Parent concept ID")
    properties: list[dict[str, Any]] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class OntologyEntityType(BaseModel):
    """An entity type in the ontology."""
    type_id: str = Field(..., description="Type UUID")
    name: str = Field(..., description="Type name")
    description: str = Field(..., description="Type description")
    parent_type_id: Optional[str] = Field(None, description="Parent type ID")
    properties: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    is_abstract: bool = Field(False, description="Whether this is an abstract type")


class OntologyRelationship(BaseModel):
    """A relationship type in the ontology."""
    relationship_id: str = Field(..., description="Relationship UUID")
    name: str = Field(..., description="Relationship name")
    description: str = Field(..., description="Relationship description")
    source_type: str = Field(..., description="Source entity type")
    target_type: str = Field(..., description="Target entity type")
    properties: list[dict[str, Any]] = Field(default_factory=list)
    cardinality: str = Field("1:1", description="Cardinality constraint")


class OntologyCapability(BaseModel):
    """A capability in the ontology."""
    capability_id: str = Field(..., description="Capability UUID")
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_parameters: list[dict[str, Any]] = Field(default_factory=list)
    output_parameters: list[dict[str, Any]] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class OntologyProperty(BaseModel):
    """A property in the ontology."""
    property_id: str = Field(..., description="Property UUID")
    name: str = Field(..., description="Property name")
    description: str = Field(..., description="Property description")
    data_type: str = Field(..., description="Data type")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    is_required: bool = Field(False, description="Whether the property is required")
    allowed_values: Optional[list[str]] = Field(None, description="Allowed values")
    related_concepts: list[str] = Field(default_factory=list)


class OntologySearchResult(BaseModel):
    """Result of an ontology search."""
    success: bool = Field(True, description="Whether the search succeeded")
    query: str = Field(..., description="The search query")
    search_type: str = Field(..., description="Type of search performed")
    concepts: list[OntologyConcept] = Field(default_factory=list)
    entity_types: list[OntologyEntityType] = Field(default_factory=list)
    relationships: list[OntologyRelationship] = Field(default_factory=list)
    capabilities: list[OntologyCapability] = Field(default_factory=list)
    properties: list[OntologyProperty] = Field(default_factory=list)
    total_count: int = Field(0, description="Total results across all types")
    has_semantic_fallback: bool = Field(False, description="Whether semantic search was used")
    error: Optional[str] = Field(None, description="Error message if any")
    error_code: Optional[str] = Field(None, description="Structured error code")


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class OntologySearchTool:
    """Search the DT-Lite ontology for concepts and definitions.

    Tool name: ``ontology_search``

    Input schema::

        {
            "query": "keyword",
            "category": "physical",
            "limit": 10,
            "search_type": "concept",
            "include_related": true,
            "semantic_search": false
        }
    """

    tool_name = "ontology_search"
    description = (
        "Search the DT-Lite ontology for concepts, entity types, "
        "capabilities, properties, and relationships. Supports keyword "
        "search with category filtering and semantic search fallback. "
        "Returns structured ontology results with hierarchical relationships. "
        "All queries are scoped to the current tenant."
    )

    SEARCH_TYPES = {"concept", "entity_type", "capability", "property", "relationship", "all"}
    CATEGORIES = {"physical", "logical", "temporal", "spatial", "abstract", "all"}

    def __init__(self, tenant_id: str, config: Optional[AIConfig] = None) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()
        self._client = httpx.AsyncClient(
            base_url=self.config.GATEWAY_URL,
            timeout=30.0,
        )
        self._semantic_enabled = False  # Will be enabled if embedding service is available

    async def execute(
        self,
        tenant_id: str,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        search_type: str = "concept",
        include_related: bool = True,
        semantic_search: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an ontology search.

        Args:
            tenant_id: Caller's tenant (validated against self.tenant_id).
            query: Search keyword.
            category: Optional concept category filter.
            limit: Max results (default 10).
            search_type: One of concept/entity_type/capability/property/relationship/all.
            include_related: Whether to include related concepts (default True).
            semantic_search: Whether to use semantic search fallback (default False).
            **kwargs: Ignored extra parameters.

        Returns:
            Dict with structured ontology search results or an error.
        """
        # Tenant validation
        if tenant_id != self.tenant_id:
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error="tenant_mismatch",
                error_code="ACCESS_DENIED",
            ).model_dump()

        # Validate search_type
        if search_type not in self.SEARCH_TYPES:
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error=f"search_type must be one of {self.SEARCH_TYPES}",
                error_code="INVALID_SEARCH_TYPE",
            ).model_dump()

        # Validate category
        if category and category not in self.CATEGORIES:
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error=f"category must be one of {self.CATEGORIES}",
                error_code="INVALID_CATEGORY",
            ).model_dump()

        # Validate limit
        if limit < 1 or limit > 100:
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error="limit must be between 1 and 100",
                error_code="INVALID_LIMIT",
            ).model_dump()

        try:
            if search_type == "all":
                return await self._search_all(
                    query=query,
                    category=category,
                    limit=limit,
                    include_related=include_related,
                    semantic_search=semantic_search,
                )
            elif search_type == "concept":
                return await self._search_concepts(
                    query=query,
                    category=category,
                    limit=limit,
                    include_related=include_related,
                    semantic_search=semantic_search,
                )
            elif search_type == "entity_type":
                return await self._search_entity_types(
                    query=query,
                    category=category,
                    limit=limit,
                )
            elif search_type == "capability":
                return await self._search_capabilities(
                    query=query,
                    limit=limit,
                )
            elif search_type == "property":
                return await self._search_properties(
                    query=query,
                    limit=limit,
                )
            elif search_type == "relationship":
                return await self._search_relationships(
                    query=query,
                    limit=limit,
                )
            else:
                return OntologySearchResult(
                    success=False,
                    query=query or "",
                    search_type=search_type,
                    error=f"Unknown search_type: {search_type}",
                    error_code="UNKNOWN_SEARCH_TYPE",
                ).model_dump()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_detail = exc.response.text if exc.response.text else str(exc)

            if status_code == 404:
                logger.warning("Ontology search 404: %s", error_detail)
                return OntologySearchResult(
                    success=False,
                    query=query or "",
                    search_type=search_type,
                    error="not_found",
                    error_code="NOT_FOUND",
                    message="No ontology elements found matching the query",
                ).model_dump()
            elif status_code == 400:
                logger.warning("Ontology search 400: %s", error_detail)
                return OntologySearchResult(
                    success=False,
                    query=query or "",
                    search_type=search_type,
                    error="bad_request",
                    error_code="BAD_REQUEST",
                    message=f"Invalid ontology search request: {error_detail}",
                ).model_dump()
            elif status_code == 500:
                logger.error("Ontology search 500: %s", error_detail)
                return OntologySearchResult(
                    success=False,
                    query=query or "",
                    search_type=search_type,
                    error="internal_error",
                    error_code="INTERNAL_ERROR",
                    message="Ontology service internal error",
                ).model_dump()
            else:
                logger.warning("Ontology search HTTP error %d: %s", status_code, error_detail)
                return OntologySearchResult(
                    success=False,
                    query=query or "",
                    search_type=search_type,
                    error=f"http_{status_code}",
                    error_code=f"HTTP_{status_code}",
                    message=f"Ontology search failed with status {status_code}",
                ).model_dump()
        except httpx.TimeoutException:
            logger.error("Ontology search timeout after 30s")
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error="timeout",
                error_code="TIMEOUT",
                message="Ontology search timed out after 30 seconds",
            ).model_dump()
        except httpx.ConnectError as exc:
            logger.error("Ontology search connection error: %s", exc)
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error="connection_error",
                error_code="CONNECTION_ERROR",
                message=f"Failed to connect to ontology service: {exc}",
            ).model_dump()
        except Exception as exc:
            logger.error("Ontology search unexpected error: %s", exc, exc_info=True)
            return OntologySearchResult(
                success=False,
                query=query or "",
                search_type=search_type,
                error="unexpected_error",
                error_code="UNEXPECTED_ERROR",
                message=f"Unexpected error during ontology search: {exc}",
            ).model_dump()

    async def _search_concepts(
        self,
        query: Optional[str],
        category: Optional[str],
        limit: int,
        include_related: bool,
        semantic_search: bool,
    ) -> dict[str, Any]:
        """Search ontology concepts."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if include_related:
            params["include_related"] = "true"

        semantic_used = False
        concepts = []

        # Try keyword search first
        try:
            resp = await self._client.get(
                "/api/v1/ontology/concepts/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            concepts_data = data.get("data", data.get("results", []))
            concepts = [self._parse_concept(c) for c in concepts_data]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (404, 400):
                raise
        except Exception:
            pass

        # Fallback to semantic search if keyword search failed or was requested
        if semantic_search or not concepts:
            semantic_used = True
            concepts = await self._semantic_search_concepts(query, limit)

        total = len(concepts)
        return OntologySearchResult(
            success=True,
            query=query or "",
            search_type="concept",
            concepts=concepts,
            total_count=total,
            has_semantic_fallback=semantic_used,
        ).model_dump()

    async def _search_entity_types(
        self,
        query: Optional[str],
        category: Optional[str],
        limit: int,
    ) -> dict[str, Any]:
        """Search ontology entity types."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if category:
            params["category"] = category

        try:
            resp = await self._client.get(
                "/api/v1/ontology/entity-types/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            types_data = data.get("data", data.get("results", []))
            entity_types = [self._parse_entity_type(t) for t in types_data]
            total = data.get("total", len(entity_types))

            return OntologySearchResult(
                success=True,
                query=query or "",
                search_type="entity_type",
                entity_types=entity_types,
                total_count=total,
            ).model_dump()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return OntologySearchResult(
                    success=True,
                    query=query or "",
                    search_type="entity_type",
                    entity_types=[],
                    total_count=0,
                ).model_dump()
            raise

    async def _search_capabilities(
        self,
        query: Optional[str],
        limit: int,
    ) -> dict[str, Any]:
        """Search ontology capabilities."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query

        try:
            resp = await self._client.get(
                "/api/v1/ontology/capabilities/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            caps_data = data.get("data", data.get("results", []))
            capabilities = [self._parse_capability(c) for c in caps_data]
            total = data.get("total", len(capabilities))

            return OntologySearchResult(
                success=True,
                query=query or "",
                search_type="capability",
                capabilities=capabilities,
                total_count=total,
            ).model_dump()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return OntologySearchResult(
                    success=True,
                    query=query or "",
                    search_type="capability",
                    capabilities=[],
                    total_count=0,
                ).model_dump()
            raise

    async def _search_properties(
        self,
        query: Optional[str],
        limit: int,
    ) -> dict[str, Any]:
        """Search ontology properties."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query

        try:
            resp = await self._client.get(
                "/api/v1/ontology/properties/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            props_data = data.get("data", data.get("results", []))
            properties = [self._parse_property(p) for p in props_data]
            total = data.get("total", len(properties))

            return OntologySearchResult(
                success=True,
                query=query or "",
                search_type="property",
                properties=properties,
                total_count=total,
            ).model_dump()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return OntologySearchResult(
                    success=True,
                    query=query or "",
                    search_type="property",
                    properties=[],
                    total_count=0,
                ).model_dump()
            raise

    async def _search_relationships(
        self,
        query: Optional[str],
        limit: int,
    ) -> dict[str, Any]:
        """Search ontology relationships."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query

        try:
            resp = await self._client.get(
                "/api/v1/ontology/relationships/search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            rels_data = data.get("data", data.get("results", []))
            relationships = [self._parse_relationship(r) for r in rels_data]
            total = data.get("total", len(relationships))

            return OntologySearchResult(
                success=True,
                query=query or "",
                search_type="relationship",
                relationships=relationships,
                total_count=total,
            ).model_dump()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return OntologySearchResult(
                    success=True,
                    query=query or "",
                    search_type="relationship",
                    relationships=[],
                    total_count=0,
                ).model_dump()
            raise

    async def _search_all(
        self,
        query: Optional[str],
        category: Optional[str],
        limit: int,
        include_related: bool,
        semantic_search: bool,
    ) -> dict[str, Any]:
        """Search all ontology types."""
        results = OntologySearchResult(
            success=True,
            query=query or "",
            search_type="all",
        )

        # Search each type in parallel
        concept_result = await self._search_concepts(query, category, limit, include_related, semantic_search)
        type_result = await self._search_entity_types(query, category, limit)
        cap_result = await self._search_capabilities(query, limit)
        prop_result = await self._search_properties(query, limit)
        rel_result = await self._search_relationships(query, limit)

        # Merge results
        if concept_result.get("concepts"):
            results.concepts = [OntologyConcept(**c) if isinstance(c, dict) else c for c in concept_result.get("concepts", [])]
        if type_result.get("entity_types"):
            results.entity_types = [OntologyEntityType(**t) if isinstance(t, dict) else t for t in type_result.get("entity_types", [])]
        if cap_result.get("capabilities"):
            results.capabilities = [OntologyCapability(**c) if isinstance(c, dict) else c for c in cap_result.get("capabilities", [])]
        if prop_result.get("properties"):
            results.properties = [OntologyProperty(**p) if isinstance(p, dict) else p for p in prop_result.get("properties", [])]
        if rel_result.get("relationships"):
            results.relationships = [OntologyRelationship(**r) if isinstance(r, dict) else r for r in rel_result.get("relationships", [])]

        results.total_count = (
            len(results.concepts) + len(results.entity_types) +
            len(results.capabilities) + len(results.properties) +
            len(results.relationships)
        )
        results.has_semantic_fallback = concept_result.get("has_semantic_fallback", False)

        return results.model_dump()

    async def _semantic_search_concepts(
        self,
        query: Optional[str],
        limit: int,
    ) -> list[OntologyConcept]:
        """Fallback semantic search for concepts using embeddings."""
        if not query:
            return []

        try:
            # Try to get embeddings from the AI service
            resp = await self._client.post(
                "/api/v1/ai/embeddings",
                json={"texts": [query]},
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            embedding_data = resp.json()
            embedding = embedding_data.get("data", [{}])[0].get("embedding")

            if not embedding:
                return []

            # Search ontology with semantic similarity
            params = {
                "embedding": embedding[:128],  # Truncate if needed
                "limit": limit,
            }
            resp = await self._client.get(
                "/api/v1/ontology/concepts/semantic-search",
                params=params,
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            concepts_data = data.get("data", data.get("results", []))
            return [self._parse_concept(c) for c in concepts_data]

        except Exception as exc:
            logger.warning("Semantic search fallback failed: %s", exc)
            return []

    def _parse_concept(self, data: dict[str, Any]) -> OntologyConcept:
        """Parse a concept from API response."""
        return OntologyConcept(
            concept_id=data.get("id", data.get("concept_id", "")),
            name=data.get("name", data.get("label", "")),
            description=data.get("description", data.get("definition", "")),
            category=data.get("category", data.get("type", "unknown")),
            parent_concept_id=data.get("parent_id", data.get("parent_concept_id")),
            properties=data.get("properties", []),
            related_concepts=data.get("related_concepts", data.get("related", [])),
            examples=data.get("examples", []),
        )

    def _parse_entity_type(self, data: dict[str, Any]) -> OntologyEntityType:
        """Parse an entity type from API response."""
        return OntologyEntityType(
            type_id=data.get("id", data.get("type_id", "")),
            name=data.get("name", data.get("label", "")),
            description=data.get("description", data.get("definition", "")),
            parent_type_id=data.get("parent_id", data.get("parent_type_id")),
            properties=data.get("properties", []),
            relationships=data.get("relationships", []),
            capabilities=data.get("capabilities", []),
            is_abstract=data.get("is_abstract", data.get("abstract", False)),
        )

    def _parse_relationship(self, data: dict[str, Any]) -> OntologyRelationship:
        """Parse a relationship from API response."""
        return OntologyRelationship(
            relationship_id=data.get("id", data.get("relationship_id", "")),
            name=data.get("name", data.get("label", "")),
            description=data.get("description", data.get("definition", "")),
            source_type=data.get("source_type", data.get("from_type", "")),
            target_type=data.get("target_type", data.get("to_type", "")),
            properties=data.get("properties", []),
            cardinality=data.get("cardinality", "1:1"),
        )

    def _parse_capability(self, data: dict[str, Any]) -> OntologyCapability:
        """Parse a capability from API response."""
        return OntologyCapability(
            capability_id=data.get("id", data.get("capability_id", "")),
            name=data.get("name", data.get("label", "")),
            description=data.get("description", data.get("definition", "")),
            input_parameters=data.get("input_parameters", data.get("inputs", [])),
            output_parameters=data.get("output_parameters", data.get("outputs", [])),
            required_roles=data.get("required_roles", data.get("roles", [])),
            constraints=data.get("constraints", []),
        )

    def _parse_property(self, data: dict[str, Any]) -> OntologyProperty:
        """Parse a property from API response."""
        return OntologyProperty(
            property_id=data.get("id", data.get("property_id", "")),
            name=data.get("name", data.get("label", "")),
            description=data.get("description", data.get("definition", "")),
            data_type=data.get("data_type", data.get("type", "string")),
            unit=data.get("unit"),
            is_required=data.get("is_required", data.get("required", False)),
            allowed_values=data.get("allowed_values", data.get("enum")),
            related_concepts=data.get("related_concepts", []),
        )

    async def get_concept_hierarchy(
        self,
        tenant_id: str,
        concept_id: str,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Get the hierarchy tree for a concept.

        Args:
            tenant_id: Caller's tenant.
            concept_id: Concept UUID.
            max_depth: Maximum tree depth.

        Returns:
            Dict with concept hierarchy tree.
        """
        if tenant_id != self.tenant_id:
            return {"success": False, "error": "tenant_mismatch"}

        try:
            resp = await self._client.get(
                f"/api/v1/ontology/concepts/{concept_id}/hierarchy",
                headers={"X-Tenant-ID": self.tenant_id},
                params={"max_depth": max_depth},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data.get("data", data)}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"success": False, "error": "concept_not_found"}
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("Concept hierarchy error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "OntologySearchTool":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
