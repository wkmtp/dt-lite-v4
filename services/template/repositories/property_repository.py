"""Template property repository — data access for template_properties table."""
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.base import TenantAwareRepository
from services.template.models import TemplateProperty


class TemplatePropertyRepository(TenantAwareRepository[TemplateProperty]):
    """Repository for TemplateProperty CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=TemplateProperty, tenant_id_column="template_id")

    async def get_by_template_and_name(self, template_id: UUID, name: str) -> Optional[TemplateProperty]:
        """Get a property by template and name."""
        stmt = select(TemplateProperty).where(
            TemplateProperty.template_id == template_id,
            TemplateProperty.name == name,
            TemplateProperty.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_template(self, template_id: UUID, limit: int = 100) -> Sequence[TemplateProperty]:
        """List all properties for a template."""
        stmt = select(TemplateProperty).where(
            TemplateProperty.template_id == template_id,
            TemplateProperty.deleted_at.is_(None),
        ).order_by(TemplateProperty.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_template(self, template_id: UUID) -> int:
        """Count properties for a template."""
        stmt = select(TemplateProperty).where(
            TemplateProperty.template_id == template_id,
            TemplateProperty.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
