"""Template domain models — SQLAlchemy 2.x Typed ORM Style."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class TwinTemplate(Base, SoftDeleteMixin):
    """Reusable digital twin type definition for an industry/domain.

    Templates define the schema for twin entities without hardcoding
    industry-specific logic in the core kernel.
    """

    __tablename__ = "twin_templates"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_template_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general"
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_definition: Mapped[dict] = mapped_column(
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
    properties: Mapped[list["TemplateProperty"]] = relationship(
        "TemplateProperty", back_populates="template", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["TemplateRelationship"]] = relationship(
        "TemplateRelationship", back_populates="template", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class TemplateProperty(Base, SoftDeleteMixin):
    """Attribute definition within a twin template."""

    __tablename__ = "template_properties"

    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_prop_template_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    template: Mapped["TwinTemplate"] = relationship(
        "TwinTemplate", back_populates="properties"
    )


class TemplateRelationship(Base, SoftDeleteMixin):
    """Allowed semantic relationships defined at the template level."""

    __tablename__ = "template_relationships"

    __table_args__ = (
        UniqueConstraint(
            "template_id", "relationship_type", "target_template",
            name="uq_rel_template_type_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_template: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    template: Mapped["TwinTemplate"] = relationship(
        "TwinTemplate", back_populates="relationships"
    )
