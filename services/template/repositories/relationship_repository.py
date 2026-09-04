"""Template relationship repository — data access for template_relationships table."""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.template.models import TemplateRelationship


class TemplateRelationshipRepository(TenantAwareRepository[TemplateRelationship]):
    """Repository for TemplateRelationship CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TemplateRelationship, tenant_id_column="template_id")

    async def list_by_template(self, template_id: UUID) -> Sequence[TemplateRelationship]:
        """List all relationships for a template."""
        stmt = select(TemplateRelationship).where(
            TemplateRelationship.template_id == template_id,
            TemplateRelationship.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_template(self, template_id: UUID) -> int:
        """Count relationships for a template."""
        stmt = select(TemplateRelationship).where(
            TemplateRelationship.template_id == template_id,
            TemplateRelationship.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
