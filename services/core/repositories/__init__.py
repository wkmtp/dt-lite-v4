"""Core Repositories Package"""
from services.core.repositories.asset_repository import AssetRepository
from services.core.repositories.entity_repository import EntityRepository
from services.core.repositories.property_repository import PropertyRepository
from services.core.repositories.relationship_repository import RelationshipRepository

# Alias for backward compatibility
PropertyDefinitionRepository = PropertyRepository
PropertyValueRepository = PropertyRepository

__all__ = [
    "EntityRepository",
    "AssetRepository",
    "PropertyRepository",
    "RelationshipRepository",
    "PropertyDefinitionRepository",
    "PropertyValueRepository",
]
