"""Ontology repositories — data access layer extending TenantAwareRepository."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.ontology.models import (
    CapabilityDefinition,
    EntityTypeDefinition,
    OntologyConcept,
    SemanticProperty,
    TemplateCapabilityBinding,
)


class OntologyRepository(TenantAwareRepository[OntologyConcept]):
    """Repository for ontology concept queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=OntologyConcept)

    async def list_active(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[OntologyConcept]:
        """List active concepts for tenant with pagination."""
        stmt = (
            select(OntologyConcept)
            .where(
                OntologyConcept.tenant_id == tenant_id,
                OntologyConcept.deleted_at.is_(None),
            )
            .order_by(OntologyConcept.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[OntologyConcept]:
        """Get concept by code within tenant scope."""
        stmt = select(OntologyConcept).where(
            OntologyConcept.code == code.lower(),
            OntologyConcept.tenant_id == tenant_id,
            OntologyConcept.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: UUID, tenant_id: UUID) -> Sequence[OntologyConcept]:
        """Get child concepts of a parent."""
        stmt = select(OntologyConcept).where(
            OntologyConcept.parent_id == parent_id,
            OntologyConcept.tenant_id == tenant_id,
            OntologyConcept.deleted_at.is_(None),
        ).order_by(OntologyConcept.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active (non-deleted) concepts for tenant."""
        stmt = select(func.count()).select_from(OntologyConcept).where(
            OntologyConcept.tenant_id == tenant_id,
            OntologyConcept.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class EntityTypeRepository(TenantAwareRepository[EntityTypeDefinition]):
    """Repository for entity type definition queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=EntityTypeDefinition)

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[EntityTypeDefinition]:
        """Get entity type by code within tenant scope."""
        stmt = select(EntityTypeDefinition).where(
            EntityTypeDefinition.code == code.lower(),
            EntityTypeDefinition.tenant_id == tenant_id,
            EntityTypeDefinition.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_concept(self, ontology_id: UUID, tenant_id: UUID) -> Sequence[EntityTypeDefinition]:
        """List entity types under a specific ontology concept."""
        stmt = select(EntityTypeDefinition).where(
            EntityTypeDefinition.ontology_id == ontology_id,
            EntityTypeDefinition.tenant_id == tenant_id,
            EntityTypeDefinition.deleted_at.is_(None),
        ).order_by(EntityTypeDefinition.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active entity types for tenant."""
        stmt = select(func.count()).select_from(EntityTypeDefinition).where(
            EntityTypeDefinition.tenant_id == tenant_id,
            EntityTypeDefinition.deleted_at.is_(None),
            EntityTypeDefinition.status == "active",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class CapabilityRepository(TenantAwareRepository[CapabilityDefinition]):
    """Repository for capability definition queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=CapabilityDefinition)

    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[CapabilityDefinition]:
        """Get capability by code within tenant scope."""
        stmt = select(CapabilityDefinition).where(
            CapabilityDefinition.code == code,
            CapabilityDefinition.tenant_id == tenant_id,
            CapabilityDefinition.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active(self, tenant_id: UUID) -> int:
        """Count active capabilities for tenant."""
        stmt = select(func.count()).select_from(CapabilityDefinition).where(
            CapabilityDefinition.tenant_id == tenant_id,
            CapabilityDefinition.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class SemanticPropertyRepository(TenantAwareRepository[SemanticProperty]):
    """Repository for semantic property queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=SemanticProperty, tenant_id_column="capability_id")

    async def list_by_capability(self, capability_id: UUID) -> Sequence[SemanticProperty]:
        """List all properties for a capability."""
        stmt = select(SemanticProperty).where(
            SemanticProperty.capability_id == capability_id,
            SemanticProperty.deleted_at.is_(None),
        ).order_by(SemanticProperty.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capability(self, capability_id: UUID) -> int:
        """Count properties for a capability."""
        stmt = select(SemanticProperty).where(
            SemanticProperty.capability_id == capability_id,
            SemanticProperty.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())


class TemplateCapabilityRepository(TenantAwareRepository[TemplateCapabilityBinding]):
    """Repository for template-capability binding queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TemplateCapabilityBinding, tenant_id_column="template_id")

    async def list_by_template(self, template_id: UUID) -> Sequence[TemplateCapabilityBinding]:
        """List all capability bindings for a template."""
        stmt = select(TemplateCapabilityBinding).where(
            TemplateCapabilityBinding.template_id == template_id,
            TemplateCapabilityBinding.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_template(self, template_id: UUID) -> int:
        """Count capability bindings for a template."""
        stmt = select(TemplateCapabilityBinding).where(
            TemplateCapabilityBinding.template_id == template_id,
            TemplateCapabilityBinding.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
