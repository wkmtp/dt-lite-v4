"""Core Domain Models - SQLAlchemy 2.x Typed ORM Style

All models use Mapped[] and mapped_column() instead of legacy Column().
All models inherit from Base (UnifiedBase) and SoftDeleteMixin.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class Entity(Base, SoftDeleteMixin):
    """Entity represents a digital twin entity in the system."""
    
    __tablename__ = "entities"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        default=None
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'")
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    property_values: Mapped[list["PropertyValue"]] = relationship(
        "PropertyValue",
        back_populates="entity",
        cascade="all, delete-orphan"
    )
    source_relationships: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    target_relationships: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )
    
    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class Asset(Base, SoftDeleteMixin):
    """Asset represents a physical or logical asset linked to an Entity."""
    
    __tablename__ = "assets"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    asset_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True
    )
    asset_class: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'")
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(255),
        default=None
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(255),
        default=None
    )
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(255),
        default=None
    )
    installed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="assets"
    )
    
    @property
    def is_active(self) -> bool:
        return self.lifecycle_status == "active" and not self.is_deleted


class PropertyDefinition(Base, SoftDeleteMixin):
    """PropertyDefinition defines the schema for properties on Entities."""
    
    __tablename__ = "property_definitions"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "key", name="uq_property_def_tenant"),
    )
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    tenant_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=True,
        index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    key: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    data_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(32),
        default=None
    )
    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    writable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    property_values: Mapped[list["PropertyValue"]] = relationship(
        "PropertyValue",
        back_populates="definition",
        cascade="all, delete-orphan"
    )
    
    @property
    def is_system_level(self) -> bool:
        return self.tenant_id is None


class PropertyValue(Base):
    """PropertyValue stores the actual value for a property on an Entity."""
    
    __tablename__ = "property_values"
    
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        primary_key=True
    )
    property_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("property_definitions.id", ondelete="CASCADE"),
        primary_key=True
    )
    value: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=None
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="property_values"
    )
    definition: Mapped["PropertyDefinition"] = relationship(
        "PropertyDefinition",
        back_populates="property_values"
    )


class Relationship(Base, SoftDeleteMixin):
    """Relationship defines connections between Entities."""
    
    __tablename__ = "relationships"
    
    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "relation_type", 
                        name="uq_relationship_type"),
    )
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    source_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    relation_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    source_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="source_relationships"
    )
    target_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="target_relationships"
    )
