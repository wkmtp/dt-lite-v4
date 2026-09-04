"""Identity Domain Models - SQLAlchemy 2.x Typed ORM Style

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


class Tenant(Base, SoftDeleteMixin):
    """Tenant represents an organization in the multi-tenant system."""
    
    __tablename__ = "tenants"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True
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
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    
    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class User(Base, SoftDeleteMixin):
    """User represents a user account within a tenant."""
    
    __tablename__ = "users"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
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
    username: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        default=None
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
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
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users"
    )
    
    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class Role(Base, SoftDeleteMixin):
    """Role represents a role within a tenant for RBAC."""
    
    __tablename__ = "roles"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),
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
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="roles"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles"
    )


class Permission(Base, SoftDeleteMixin):
    """Permission represents a system-wide permission (not tenant-scoped)."""
    
    __tablename__ = "permissions"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        default=None
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions"
    )


# Junction tables (no soft delete needed for association tables)
class UserRole(Base):
    """UserRole is a junction table between User and Role."""
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )


class RolePermission(Base):
    """RolePermission is a junction table between Role and Permission."""
    
    __tablename__ = "role_permissions"
    
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True
    )
