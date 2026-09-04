"""Ontology domain models — Semantic Meta Model for zero-code twin generation.

All models use SQLAlchemy 2.x Typed ORM style (Mapped[] + mapped_column()).
All models extend Base and SoftDeleteMixin.
All queries are tenant-scoped via TenantAwareRepository.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class OntologyConcept(Base, SoftDeleteMixin):
    """Semantic classification concept in a hierarchical ontology tree.

    Example hierarchy:
        Building (root)
          ├─ HVAC
          │   ├─ AHU
          │   └─ VAV
          └─ Lighting
    """

    __tablename__ = "ontology_concepts"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_concept_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("ontology_concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships (lazy-load only, no cascade — ontology is reference data)
    parent: Mapped[Optional["OntologyConcept"]] = relationship(
        "OntologyConcept",
        back_populates="children",
        remote_side=[id],
    )
    children: Mapped[list["OntologyConcept"]] = relationship(
        "OntologyConcept",
        back_populates="parent",
        remote_side=[parent_id],
    )
    entity_types: Mapped[list["EntityTypeDefinition"]] = relationship(
        "EntityTypeDefinition", back_populates="concept"
    )

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def is_active(self) -> bool:
        return not self.is_deleted


class EntityTypeDefinition(Base, SoftDeleteMixin):
    """Defines what kind of twin object can be generated from a template.

    This is a META model — it describes entity types without creating runtime twins.
    Linking to capabilities defines what properties/state each type supports.
    """

    __tablename__ = "entity_type_definitions"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_etype_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    ontology_id: Mapped[UUID] = mapped_column(
        ForeignKey("ontology_concepts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    property_schema: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}::jsonb"
    )
    allowed_capabilities: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}::jsonb"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="'active'"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    concept: Mapped["OntologyConcept"] = relationship(
        "OntologyConcept", back_populates="entity_types"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class CapabilityDefinition(Base, SoftDeleteMixin):
    """Reusable ability model — industry-neutral semantic capability.

    Examples: TemperatureMeasurement, PowerMeasurement, MotionControl
    NOT examples: HVACCapability, RobotCapability (those would be industry-specific)
    """

    __tablename__ = "capability_definitions"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_capability_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_definition: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}::jsonb"
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    properties: Mapped[list["SemanticProperty"]] = relationship(
        "SemanticProperty", back_populates="capability", cascade="all, delete-orphan"
    )
    template_bindings: Mapped[list["TemplateCapabilityBinding"]] = relationship(
        "TemplateCapabilityBinding",
        back_populates="capability",
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self) -> bool:
        return not self.is_deleted


class SemanticProperty(Base, SoftDeleteMixin):
    """Standard data meaning within a capability.

    Examples: temperature (float, °C), voltage (float, V), speed (float, rpm)
    """

    __tablename__ = "semantic_properties"

    __table_args__ = (
        UniqueConstraint("capability_id", "name", name="uq_prop_capability_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    capability_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    capability: Mapped["CapabilityDefinition"] = relationship(
        "CapabilityDefinition", back_populates="properties"
    )


class CapabilityPropertyBinding(Base):
    """Junction table: which semantic properties belong to which capability.

    Note: SemanticProperty already has capability_id FK, so this is redundant.
    Kept as explicit binding for query clarity in complex joins.
    """

    __tablename__ = "capability_property_bindings"

    capability_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_definitions.id", ondelete="CASCADE"), primary_key=True
    )
    property_id: Mapped[UUID] = mapped_column(
        ForeignKey("semantic_properties.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class TemplateCapabilityBinding(Base, SoftDeleteMixin):
    """Connects a Template to a Capability — defines which capabilities a template requires.

    Example: SmartBuilding template requires TemperatureMeasurement, OccupancyDetection
    """

    __tablename__ = "template_capability_bindings"

    __table_args__ = (
        UniqueConstraint(
            "template_id", "capability_id", name="uq_tpc_template_capability",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capability_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships (forward-only to avoid circular registry issues)
    capability: Mapped["CapabilityDefinition"] = relationship(
        "CapabilityDefinition", back_populates="template_bindings"
    )
