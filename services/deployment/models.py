"""Deployment domain models — Semantic deployment meta model.

All models use SQLAlchemy 2.x Typed ORM style (Mapped[] + mapped_column()).
All models extend Base and SoftDeleteMixin.
All queries are tenant-scoped via TenantAwareRepository.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class DeploymentProfile(Base, SoftDeleteMixin):
    """Reusable deployment blueprint for a template.

    A profile defines how a template should be instantiated:
    which nodes to create, their types, and required capabilities.

    Example: SmartBuilding profile requires TemperatureMeasurement,
    OccupancyDetection, EnergyConsumption capabilities.
    """

    __tablename__ = "deployment_profiles"

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_profile_tenant_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="'draft'"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    instances: Mapped[list["DeploymentInstance"]] = relationship(
        "DeploymentInstance", back_populates="profile", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class DeploymentInstance(Base, SoftDeleteMixin):
    """An instantiated deployment from a profile into an operational environment.

    Lifecycle states:
    - DRAFT: Created but not validated
    - VALIDATING: Being checked against requirements
    - READY: Validation passed, ready to deploy
    - DEPLOYED: Active in environment
    - RUNNING: Operational state
    - OFFLINE: Temporarily unavailable
    - ARCHIVED: No longer active
    """

    __tablename__ = "deployment_instances"

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_instance_tenant_name"),
        CheckConstraint(
            "status IN ('draft', 'validating', 'ready', 'deployed', "
            "'running', 'offline', 'archived')",
            name="ck_instance_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("deployment_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="'draft'",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    profile: Mapped["DeploymentProfile"] = relationship(
        "DeploymentProfile", back_populates="instances"
    )
    nodes: Mapped[list["DeploymentNode"]] = relationship(
        "DeploymentNode", back_populates="deployment", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status in {"ready", "deployed", "running"} and not self.is_deleted


class DeploymentNode(Base, SoftDeleteMixin):
    """Logical deployment location/object within an instance.

    Represents WHERE something is deployed, NOT WHAT it is (that's TwinEntity).
    Examples:
    - Building: "AHU Room 101"
    - Manufacturing: "Production Station A"
    - Energy: "PV Array Row 3"
    """

    __tablename__ = "deployment_nodes"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "deployment_id", "name", name="uq_node_tenant_deploy_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    deployment_id: Mapped[UUID] = mapped_column(
        ForeignKey("deployment_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(128), nullable=False, default="generic")
    entity_type_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("entity_type_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    deployment: Mapped["DeploymentInstance"] = relationship(
        "DeploymentInstance", back_populates="nodes"
    )
    capabilities: Mapped[list["DeploymentNodeCapability"]] = relationship(
        "DeploymentNodeCapability", back_populates="node", cascade="all, delete-orphan"
    )


class DeploymentNodeCapability(Base, SoftDeleteMixin):
    """Binds a capability to a deployment node with configuration.

    Links DeploymentNode to CapabilityDefinition without protocol fields.
    This enables zero-code capability injection at deployment time.
    """

    __tablename__ = "deployment_node_capabilities"

    __table_args__ = (
        UniqueConstraint(
            "node_id", "capability_id", name="uq_node_capability",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("deployment_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    configuration_schema: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}::jsonb"
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships (forward-only to avoid circular registry issues)
    node: Mapped["DeploymentNode"] = relationship(
        "DeploymentNode", back_populates="capabilities"
    )

    @property
    def is_required(self) -> bool:
        return self.required
