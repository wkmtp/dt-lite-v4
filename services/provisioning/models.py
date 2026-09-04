"""Provisioning domain models — Planning and tracking twin instantiation."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class ProvisioningPlan(Base, SoftDeleteMixin):
    """Represents a complete provisioning plan for a DeploymentInstance.

    A plan is generated from a DeploymentInstance and describes what
    TwinEntities and relationships need to be created.
    """

    __tablename__ = "provisioning_plans"

    __table_args__ = (
        UniqueConstraint("tenant_id", "deployment_instance_id", name="uq_plan_deployment"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    deployment_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("deployment_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft",
        server_default="'draft'",
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    items: Mapped[list["ProvisioningItem"]] = relationship(
        "ProvisioningItem", back_populates="plan", cascade="all, delete-orphan"
    )
    executions: Mapped[list["ProvisioningExecution"]] = relationship(
        "ProvisioningExecution", back_populates="plan", cascade="all, delete-orphan"
    )

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class ProvisioningItem(Base, SoftDeleteMixin):
    """Individual action within a provisioning plan.

    Each item represents one TwinEntity creation or one TwinRelationship creation.
    """

    __tablename__ = "provisioning_items"

    __table_args__ = (
        UniqueConstraint(
            "plan_id", "external_id", "action", name="uq_item_plan_external_action",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("provisioning_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_type_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("entity_type_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CREATE_ENTITY"
    )
    source_external_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    target_external_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    rel_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_twin_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_twin_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        server_default="'pending'"
    )
    created_twin_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    plan: Mapped["ProvisioningPlan"] = relationship(
        "ProvisioningPlan", back_populates="items"
    )

    @property
    def is_entity_creation(self) -> bool:
        return self.action == "CREATE_ENTITY"

    @property
    def is_relationship_creation(self) -> bool:
        return self.action == "CREATE_RELATIONSHIP"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class ProvisioningExecution(Base, SoftDeleteMixin):
    """Execution record for a provisioning plan run."""

    __tablename__ = "provisioning_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("provisioning_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="started",
        server_default="'started'"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    items_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    plan: Mapped["ProvisioningPlan"] = relationship(
        "ProvisioningPlan", back_populates="executions"
    )

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"
