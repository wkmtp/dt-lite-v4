"""Ontology service layer — business logic for semantic meta model operations."""
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select

from services.ontology.exceptions import (
    CircularReferenceError,
    ConceptNotFoundError,
    DuplicateCodeError,
    EntityTypeNotFoundError,
    InvalidSchemaError,
    ParentNotfoundError,
)
from services.ontology.models import (
    CapabilityDefinition,
    EntityTypeDefinition,
    OntologyConcept,
    SemanticProperty,
)
from services.ontology.repository import (
    CapabilityRepository,
    EntityTypeRepository,
    OntologyRepository,
)
from services.ontology.schemas import (
    CapabilityCreateRequest,
    CapabilityUpdateRequest,
    ConceptCreateRequest,
    ConceptUpdateRequest,
    EntityTypeCreateRequest,
    EntityTypeUpdateRequest,
    SemanticPropertyCreateRequest,
)
from services.ontology.validators import (
    CapabilitySchemaValidator,
    EntityTypeValidator,
    OntologyConceptValidator,
)


class OntologyService:
    """Service layer for ontology concept hierarchy management."""

    def __init__(self, repository: OntologyRepository):
        self._repo = repository

    async def create_concept(self, request: ConceptCreateRequest, tenant_id: UUID) -> OntologyConcept:
        """Create a new ontology concept."""
        existing = await self._repo.get_by_code(request.code, tenant_id)
        if existing is not None:
            raise DuplicateCodeError("Concept", request.code)

        if not OntologyConceptValidator.validate_category(request.category):
            raise ValueError(f"Invalid category: {request.category}")

        if request.parent_id is not None:
            parent = await self._repo.get_by_id_for_tenant(request.parent_id, tenant_id)
            if parent is None:
                raise ParentNotfoundError(request.parent_id)
            if await self._would_create_cycle(request.parent_id, request.parent_id, tenant_id):
                raise CircularReferenceError("new-concept", str(request.parent_id))

        concept = OntologyConcept(
            id=uuid4(),
            tenant_id=tenant_id,
            code=request.code.lower(),
            name=request.name,
            category=request.category.lower(),
            parent_id=request.parent_id,
            description=request.description,
            version=request.version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await self._repo.create(concept)
        return concept

    async def get_concept(self, concept_id: UUID, tenant_id: UUID) -> OntologyConcept:
        """Get concept by ID with tenant isolation."""
        concept = await self._repo.get_by_id_for_tenant(concept_id, tenant_id)
        if concept is None or concept.is_deleted:
            raise ConceptNotFoundError(concept_id)
        return concept

    async def update_concept(self, concept_id: UUID, request: ConceptUpdateRequest, tenant_id: UUID) -> OntologyConcept:
        """Update concept fields."""
        concept = await self.get_concept(concept_id, tenant_id)

        if request.name is not None:
            concept.name = request.name
        if request.description is not None:
            concept.description = request.description
        if request.parent_id is not None:
            parent = await self._repo.get_by_id_for_tenant(request.parent_id, tenant_id)
            if parent is None:
                raise ParentNotfoundError(request.parent_id)
            if await self._would_create_cycle(request.parent_id, concept_id, tenant_id):
                raise CircularReferenceError(str(concept_id), str(request.parent_id))
            concept.parent_id = request.parent_id

        concept.updated_at = datetime.now(timezone.utc)
        await self._repo.session.flush()
        await self._repo.session.refresh(concept)
        return concept

    async def get_tree(self, root_id: Optional[UUID], tenant_id: UUID) -> list[dict]:
        """Get full concept tree starting from optional root."""
        if root_id is None:
            stmt = select(OntologyConcept).where(
                OntologyConcept.parent_id.is_(None),
                OntologyConcept.tenant_id == tenant_id,
                OntologyConcept.deleted_at.is_(None),
            ).order_by(OntologyConcept.name)
            result = await self._repo.session.execute(stmt)
            roots = result.scalars().all()
        else:
            roots = [await self.get_concept(root_id, tenant_id)]

        return [self._build_node(c) for c in roots]

    def _build_node(self, concept: OntologyConcept) -> dict:
        """Build recursive node structure."""
        stmt = select(OntologyConcept).where(
            OntologyConcept.parent_id == concept.id,
            OntologyConcept.tenant_id == concept.tenant_id,
            OntologyConcept.deleted_at.is_(None),
        ).order_by(OntologyConcept.name)
        result = self._repo.session.execute(stmt)
        children = result.scalars().all()
        return {
            "id": str(concept.id),
            "code": concept.code,
            "name": concept.name,
            "category": concept.category,
            "children": [self._build_node(c) for c in children],
        }

    async def _would_create_cycle(self, new_parent_id: UUID, self_id: UUID, tenant_id: UUID, depth: int = 0) -> bool:
        """Check if setting new_parent would create a cycle."""
        if depth > 100:
            return True
        if new_parent_id == self_id:
            return True
        parent = await self._repo.get_by_id_for_tenant(new_parent_id, tenant_id)
        if parent is None or parent.parent_id is None:
            return False
        return await self._would_create_cycle(parent.parent_id, self_id, tenant_id, depth + 1)


class EntityTypeService:
    """Service layer for entity type definition management."""

    def __init__(self, repository: EntityTypeRepository):
        self._repo = repository

    async def create_entity_type(self, request: EntityTypeCreateRequest, tenant_id: UUID) -> EntityTypeDefinition:
        """Create a new entity type definition."""
        existing = await self._repo.get_by_code(request.code, tenant_id)
        if existing is not None:
            raise DuplicateCodeError("EntityType", request.code)

        errors = EntityTypeValidator.validate_property_schema(request.property_schema)
        if errors:
            raise InvalidSchemaError("; ".join(errors))

        entity_type = EntityTypeDefinition(
            id=uuid4(),
            tenant_id=tenant_id,
            ontology_id=request.ontology_id,
            code=request.code.lower(),
            name=request.name,
            description=request.description,
            icon=request.icon,
            property_schema=request.property_schema,
            allowed_capabilities=request.allowed_capabilities,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await self._repo.create(entity_type)
        return entity_type

    async def get_entity_type(self, entity_type_id: UUID, tenant_id: UUID) -> EntityTypeDefinition:
        """Get entity type by ID with tenant isolation."""
        entity_type = await self._repo.get_by_id_for_tenant(entity_type_id, tenant_id)
        if entity_type is None or entity_type.is_deleted:
            raise EntityTypeNotFoundError(entity_type_id)
        return entity_type

    async def list_types(self, tenant_id: UUID, ontology_id: Optional[UUID] = None) -> Sequence[EntityTypeDefinition]:
        """List entity types, optionally filtered by ontology concept."""
        if ontology_id is not None:
            return await self._repo.list_by_concept(ontology_id, tenant_id)
        return await self._repo.list(tenant_id)

    async def update_entity_type(
        self, entity_type_id: UUID, request: EntityTypeUpdateRequest, tenant_id: UUID
    ) -> EntityTypeDefinition:
        """Update entity type fields."""
        entity_type = await self.get_entity_type(entity_type_id, tenant_id)

        if request.name is not None:
            entity_type.name = request.name
        if request.description is not None:
            entity_type.description = request.description
        if request.icon is not None:
            entity_type.icon = request.icon
        if request.property_schema is not None:
            errors = EntityTypeValidator.validate_property_schema(request.property_schema)
            if errors:
                raise InvalidSchemaError("; ".join(errors))
            entity_type.property_schema = request.property_schema
        if request.allowed_capabilities is not None:
            entity_type.allowed_capabilities = request.allowed_capabilities
        if request.status is not None:
            entity_type.status = request.status

        entity_type.updated_at = datetime.now(timezone.utc)
        await self._repo.session.flush()
        await self._repo.session.refresh(entity_type)
        return entity_type


class CapabilityService:
    """Service layer for capability definition management."""

    def __init__(self, repository: CapabilityRepository):
        self._repo = repository

    async def create_capability(self, request: CapabilityCreateRequest, tenant_id: UUID) -> CapabilityDefinition:
        """Create a new capability definition."""
        existing = await self._repo.get_by_code(request.code, tenant_id)
        if existing is not None:
            raise DuplicateCodeError("Capability", request.code)

        errors = CapabilitySchemaValidator.validate(request.schema_definition)
        if errors:
            raise InvalidSchemaError("; ".join(errors))

        capability = CapabilityDefinition(
            id=uuid4(),
            tenant_id=tenant_id,
            code=request.code,
            name=request.name,
            description=request.description,
            schema_definition=request.schema_definition,
            version=request.version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await self._repo.create(capability)
        return capability

    async def get_capability(self, capability_id: UUID, tenant_id: UUID) -> CapabilityDefinition:
        """Get capability by ID with tenant isolation."""
        capability = await self._repo.get_by_id_for_tenant(capability_id, tenant_id)
        if capability is None or capability.is_deleted:
            raise ConceptNotFoundError(capability_id)
        return capability

    async def list_capabilities(self, tenant_id: UUID) -> Sequence[CapabilityDefinition]:
        """List all capabilities for tenant."""
        return await self._repo.list(tenant_id)

    async def update_capability(
        self, capability_id: UUID, request: CapabilityUpdateRequest, tenant_id: UUID
    ) -> CapabilityDefinition:
        """Update capability fields."""
        capability = await self.get_capability(capability_id, tenant_id)

        if request.name is not None:
            capability.name = request.name
        if request.description is not None:
            capability.description = request.description
        if request.schema_definition is not None:
            errors = CapabilitySchemaValidator.validate(request.schema_definition)
            if errors:
                raise InvalidSchemaError("; ".join(errors))
            capability.schema_definition = request.schema_definition
        if request.version is not None:
            capability.version = request.version

        capability.updated_at = datetime.now(timezone.utc)
        await self._repo.session.flush()
        await self._repo.session.refresh(capability)
        return capability

    async def bind_property(
        self, capability_id: UUID, request: SemanticPropertyCreateRequest, tenant_id: UUID
    ) -> SemanticProperty:
        """Add a semantic property to a capability."""
        await self.get_capability(capability_id, tenant_id)

        prop = SemanticProperty(
            id=uuid4(),
            capability_id=capability_id,
            name=request.name.lower(),
            data_type=request.data_type,
            unit=request.unit,
            description=request.description,
            required=request.required,
            created_at=datetime.now(timezone.utc),
        )

        await self._repo.session.add(prop)
        await self._repo.session.flush()
        await self._repo.session.refresh(prop)
        return prop
