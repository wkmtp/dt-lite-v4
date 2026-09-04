"""Repository Pattern for DT-Lite Core"""
from typing import Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from services.core.models.models import Entity, Asset, PropertyDefinition, PropertyValue, Relationship


class EntityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, entity_id: str, tenant_id: str) -> Optional[Entity]:
        result = await self.db.execute(
            select(Entity).where(
                Entity.id == uuid.UUID(entity_id),
                Entity.tenant_id == uuid.UUID(tenant_id)
            )
        )
        return result.scalars().first()

    async def list_by_tenant(self, tenant_id: str, entity_type: Optional[str] = None,
                             skip: int = 0, limit: int = 20) -> List[Entity]:
        query = select(Entity).where(Entity.tenant_id == uuid.UUID(tenant_id))
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, entity: Entity) -> Entity:
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity_id: str, tenant_id: str, **kwargs) -> Optional[Entity]:
        entity = await self.get_by_id(entity_id, tenant_id)
        if not entity:
            return None
        for key, value in kwargs.items():
            if hasattr(entity, key) and key not in ["id", "tenant_id", "created_at"]:
                setattr(entity, key, value)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity_id: str, tenant_id: str) -> bool:
        result = await self.db.execute(
            delete(Entity).where(
                Entity.id == uuid.UUID(entity_id),
                Entity.tenant_id == uuid.UUID(tenant_id)
            )
        )
        await self.db.commit()
        return result.rowcount > 0


class AssetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_code(self, asset_code: str) -> Optional[Asset]:
        result = await self.db.execute(select(Asset).where(Asset.asset_code == asset_code))
        return result.scalars().first()

    async def get_by_entity_id(self, entity_id: str) -> Optional[Asset]:
        result = await self.db.execute(select(Asset).where(Asset.entity_id == uuid.UUID(entity_id)))
        return result.scalars().first()

    async def list_all(self, asset_class: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[Asset]:
        query = select(Asset)
        if asset_class:
            query = query.where(Asset.asset_class == asset_class)
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, asset: Asset) -> Asset:
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def update(self, asset_id: str, **kwargs) -> Optional[Asset]:
        result = await self.db.execute(select(Asset).where(Asset.id == uuid.UUID(asset_id)))
        asset = result.scalars().first()
        if not asset:
            return None
        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset


class PropertyDefinitionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_entity_type(self, entity_type: str, tenant_id: Optional[str] = None) -> List[PropertyDefinition]:
        query = select(PropertyDefinition).where(PropertyDefinition.entity_type == entity_type)
        if tenant_id:
            query = query.where(PropertyDefinition.tenant_id == uuid.UUID(tenant_id))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, prop_def: PropertyDefinition) -> PropertyDefinition:
        self.db.add(prop_def)
        await self.db.commit()
        await self.db.refresh(prop_def)
        return prop_def


class PropertyValueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_value(self, entity_id: str, property_def_id: str) -> Optional[Any]:
        result = await self.db.execute(
            select(PropertyValue).where(
                PropertyValue.entity_id == uuid.UUID(entity_id),
                PropertyValue.property_definition_id == uuid.UUID(property_def_id)
            )
        )
        prop_value = result.scalars().first()
        return prop_value.value if prop_value else None

    async def set_value(self, entity_id: str, property_def_id: str, value: Any) -> PropertyValue:
        prop_value = PropertyValue(
            entity_id=uuid.UUID(entity_id),
            property_definition_id=uuid.UUID(property_def_id),
            value=value
        )
        self.db.add(prop_value)
        await self.db.commit()
        await self.db.refresh(prop_value)
        return prop_value


class RelationshipRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_source(self, source_entity_id: str) -> List[Relationship]:
        result = await self.db.execute(
            select(Relationship).where(Relationship.source_entity_id == uuid.UUID(source_entity_id))
        )
        return list(result.scalars().all())

    async def list_by_target(self, target_entity_id: str) -> List[Relationship]:
        result = await self.db.execute(
            select(Relationship).where(Relationship.target_entity_id == uuid.UUID(target_entity_id))
        )
        return list(result.scalars().all())

    async def list_by_tenant(self, tenant_id: str) -> List[Relationship]:
        result = await self.db.execute(
            select(Relationship).where(Relationship.tenant_id == uuid.UUID(tenant_id))
        )
        return list(result.scalars().all())

    async def create(self, relationship: Relationship) -> Relationship:
        self.db.add(relationship)
        await self.db.commit()
        await self.db.refresh(relationship)
        return relationship

    async def delete(self, rel_id: str) -> bool:
        result = await self.db.execute(
            delete(Relationship).where(Relationship.id == uuid.UUID(rel_id))
        )
        await self.db.commit()
        return result.rowcount > 0
