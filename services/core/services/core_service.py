"""Enhanced Service layer for Core domain - Entity, Asset, Property, Relationship with Graph Query"""
import uuid
from typing import Any, Dict, List, Optional

from services.core.models.models import (
    Asset,
    Entity,
    PropertyDefinition,
    PropertyValue,
    Relationship,
)
from services.core.repositories import (
    AssetRepository,
    EntityRepository,
    PropertyDefinitionRepository,
    PropertyValueRepository,
    RelationshipRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


class EntityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepository(db)

    async def create_entity(self, tenant_id: str, data: dict) -> Entity:
        entity = Entity(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            entity_type=data["entity_type"],
            name=data["name"],
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
        return await self.repo.create(entity)

    async def get_entity(self, entity_id: str, tenant_id: str) -> Optional[Entity]:
        return await self.repo.get_by_id(entity_id, tenant_id)

    async def list_entities(self, tenant_id: str, entity_type: Optional[str] = None,
                            skip: int = 0, limit: int = 20) -> List[Entity]:
        return await self.repo.list_by_tenant(tenant_id, entity_type, skip, limit)

    async def update_entity(self, entity_id: str, tenant_id: str, data: dict) -> Optional[Entity]:
        return await self.repo.update(entity_id, tenant_id, **data)

    async def delete_entity(self, entity_id: str, tenant_id: str) -> bool:
        return await self.repo.delete(entity_id, tenant_id)

    async def get_entity_graph(self, entity_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get full graph context for an entity"""
        entity = await self.get_entity(entity_id, tenant_id)
        if not entity:
            return {"error": "Entity not found"}

        repo = RelationshipRepository(self.db)
        relationships = await repo.list_by_entity(entity_id)

        # Get neighbors
        neighbors = []
        for rel in relationships:
            neighbor_id = str(rel.target_entity_id if rel.source_entity_id == entity.id else rel.source_entity_id)
            neighbors.append({
                "id": neighbor_id,
                "relation_type": rel.relation_type,
                "direction": "out" if rel.source_entity_id == entity.id else "in"
            })

        return {
            "entity": {
                "id": str(entity.id),
                "type": entity.entity_type,
                "name": entity.name,
                "status": entity.status,
            },
            "relationships": [
                {
                    "id": str(r.id),
                    "source": str(r.source_entity_id),
                    "target": str(r.target_entity_id),
                    "type": r.relation_type,
                }
                for r in relationships
            ],
            "neighbors": neighbors,
        }


class AssetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssetRepository(db)

    async def create_asset(self, data: dict) -> Asset:
        # Check entity exists
        entity_repo = EntityRepository(self.db)
        entity = await entity_repo.get_by_id(data["entity_id"], data.get("tenant_id"))
        if not entity:
            raise ValueError(f"Entity {data['entity_id']} not found")

        asset = Asset(
            id=uuid.uuid4(),
            entity_id=uuid.UUID(data["entity_id"]),
            asset_code=data["asset_code"],
            asset_class=data["asset_class"],
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            serial_number=data.get("serial_number"),
            metadata=data.get("metadata", {}),
        )
        return await self.repo.create(asset)

    async def get_asset_by_code(self, asset_code: str) -> Optional[Asset]:
        return await self.repo.get_by_code(asset_code)

    async def list_assets(self, asset_class: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[Asset]:
        return await self.repo.list_all(asset_class, skip, limit)


class PropertyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.prop_def_repo = PropertyDefinitionRepository(db)
        self.prop_value_repo = PropertyValueRepository(db)

    async def create_property_definition(self, data: dict) -> PropertyDefinition:
        prop_def = PropertyDefinition(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            entity_type=data["entity_type"],
            key=data["key"],
            data_type=data["data_type"],
            unit=data.get("unit"),
            required=bool(data.get("required", False)),
            writable=bool(data.get("writable", False)),
            extra_data=data.get("extra_data", {}),
        )
        return await self.prop_def_repo.create(prop_def)

    async def get_property_definitions(self, entity_type: str, tenant_id: Optional[str] = None) -> List[PropertyDefinition]:
        return await self.prop_def_repo.list_by_entity_type(entity_type, tenant_id)

    async def set_property_value(self, entity_id: str, property_def_id: str, value: Any) -> PropertyValue:
        return await self.prop_value_repo.set_value(entity_id, property_def_id, value)

    async def get_property_value(self, entity_id: str, property_def_id: str) -> Optional[Any]:
        return await self.prop_value_repo.get_value(entity_id, property_def_id)


class RelationshipService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationshipRepository(db)

    async def create_relationship(self, data: dict) -> Relationship:
        rel = Relationship(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(data["tenant_id"]),
            source_entity_id=uuid.UUID(data["source_entity_id"]),
            target_entity_id=uuid.UUID(data["target_entity_id"]),
            relation_type=data["relation_type"],
            extra_data=data.get("extra_data", {}),
        )
        return await self.repo.create(rel)

    async def list_relationships(self, tenant_id: str, entity_id: Optional[str] = None) -> List[Relationship]:
        if entity_id:
            return await self.repo.list_by_entity(entity_id)
        return await self.repo.list_by_tenant(tenant_id)

    async def delete_relationship(self, rel_id: str) -> bool:
        return await self.repo.delete(rel_id)
