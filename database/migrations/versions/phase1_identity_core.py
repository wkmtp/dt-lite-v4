"""Phase 1 Migration: Identity + Core Database Schema

This migration creates all tables for Phase 1:
- tenants
- users
- roles
- permissions
- user_roles (junction table)
- role_permissions (junction table)
- entities
- assets
- property_definitions
- property_values
- relationships
"""

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase1_identity_core'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=255)),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id', 'username')
    )
    
    # Create roles table
    op.create_table('roles',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id', 'code')
    )
    
    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512)),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create user_roles junction table
    op.create_table('user_roles',
        sa.Column('user_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE')
    )
    
    # Create role_permissions junction table
    op.create_table('role_permissions',
        sa.Column('role_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE')
    )
    
    # Create entities table
    op.create_table('entities',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=512)),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'])
    )
    
    # Create assets table
    op.create_table('assets',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_code', sa.String(length=128), nullable=False),
        sa.Column('asset_class', sa.String(length=128), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('manufacturer', sa.String(length=255)),
        sa.Column('model', sa.String(length=255)),
        sa.Column('serial_number', sa.String(length=255)),
        sa.Column('installed_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('entity_id'),
        sa.UniqueConstraint('asset_code')
    )
    
    # Create property_definitions table
    # NOTE: PostgreSQL UNIQUE(tenant_id, entity_type, key) does NOT handle NULL tenant_id correctly.
    # Two partial unique indexes are required:
    #   - System-level: where tenant_id IS NULL
    #   - Tenant-level: where tenant_id IS NOT NULL
    op.create_table('property_definitions',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True)),
        sa.Column('entity_type', sa.String(length=128), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=32)),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('writable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'])
    )
    # Partial unique index for system-level definitions (tenant_id IS NULL)
    op.create_index('uq_property_definition_system', 'property_definitions',
                    ['entity_type', 'key'],
                    unique=True,
                    postgresql_where=sa.text('tenant_id IS NULL'))
    # Partial unique index for tenant-level definitions (tenant_id IS NOT NULL)
    op.create_index('uq_property_definition_tenant', 'property_definitions',
                    ['tenant_id', 'entity_type', 'key'],
                    unique=True,
                    postgresql_where=sa.text('tenant_id IS NOT NULL'))
    
    # Create property_values table
    op.create_table('property_values',
        sa.Column('entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('property_definition_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('value', sapg.JSONB()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('entity_id', 'property_definition_id'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_definition_id'], ['property_definitions.id'])
    )
    
    # Create relationships table
    op.create_table('relationships',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('source_entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('target_entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(length=128), nullable=False),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['source_entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.CheckConstraint('source_entity_id != target_entity_id', name='check_self_relation')
    )
    
    # Create indexes
    op.create_index('idx_tenants_code', 'tenants', ['code'])
    op.create_index('idx_users_tenant', 'users', ['tenant_id'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_roles_tenant', 'roles', ['tenant_id'])
    op.create_index('idx_entities_tenant', 'entities', ['tenant_id'])
    op.create_index('idx_entities_type', 'entities', ['tenant_id', 'entity_type'])
    op.create_index('idx_assets_entity', 'assets', ['entity_id'])
    op.create_index('idx_assets_code', 'assets', ['asset_code'])
    op.create_index('idx_relationships_source', 'relationships', ['source_entity_id'])
    op.create_index('idx_relationships_target', 'relationships', ['target_entity_id'])
    op.create_index('idx_property_defs_type', 'property_definitions', ['entity_type'])
    
    # Insert system permissions (idempotent - using ON CONFLICT DO NOTHING)
    # Per spec 94.37 & 94.38: permissions must be seeded and must be idempotent
    op.execute("""
        INSERT INTO permissions (id, code, description, metadata) VALUES
        ('a0000000-0000-0000-0000-000000000001', 'tenant:read', 'Read tenants', '{}'),
        ('a0000000-0000-0000-0000-000000000002', 'tenant:update', 'Update tenants', '{}'),
        ('a0000000-0000-0000-0000-000000000003', 'user:read', 'Read users', '{}'),
        ('a0000000-0000-0000-0000-000000000004', 'user:create', 'Create users', '{}'),
        ('a0000000-0000-0000-0000-000000000005', 'user:update', 'Update users', '{}'),
        ('a0000000-0000-0000-0000-000000000006', 'user:delete', 'Delete users', '{}'),
        ('a0000000-0000-0000-0000-000000000007', 'role:read', 'Read roles', '{}'),
        ('a0000000-0000-0000-0000-000000000008', 'role:create', 'Create roles', '{}'),
        ('a0000000-0000-0000-0000-000000000009', 'role:update', 'Update roles', '{}'),
        ('a0000000-0000-0000-0000-00000000000a', 'role:delete', 'Delete roles', '{}'),
        ('a0000000-0000-0000-0000-00000000000b', 'entity:read', 'Read entities', '{}'),
        ('a0000000-0000-0000-0000-00000000000c', 'entity:create', 'Create entities', '{}'),
        ('a0000000-0000-0000-0000-00000000000d', 'entity:update', 'Update entities', '{}'),
        ('a0000000-0000-0000-0000-00000000000e', 'entity:delete', 'Delete entities', '{}'),
        ('a0000000-0000-0000-0000-00000000000f', 'asset:read', 'Read assets', '{}'),
        ('a0000000-0000-0000-0000-000000000010', 'asset:create', 'Create assets', '{}'),
        ('a0000000-0000-0000-0000-000000000011', 'asset:update', 'Update assets', '{}'),
        ('a0000000-0000-0000-0000-000000000012', 'asset:delete', 'Delete assets', '{}'),
        ('a0000000-0000-0000-0000-000000000013', 'property:read', 'Read properties', '{}'),
        ('a0000000-0000-0000-0000-000000000014', 'property:create', 'Create property definitions', '{}'),
        ('a0000000-0000-0000-0000-000000000015', 'property:update', 'Update properties', '{}'),
        ('a0000000-0000-0000-0000-000000000016', 'property:delete', 'Delete properties', '{}'),
        ('a0000000-0000-0000-0000-000000000017', 'relationship:read', 'Read relationships', '{}'),
        ('a0000000-0000-0000-0000-000000000018', 'relationship:create', 'Create relationships', '{}'),
        ('a0000000-0000-0000-0000-000000000019', 'relationship:delete', 'Delete relationships', '{}')
        ON CONFLICT (code) DO NOTHING
    """)
    
    # NOTE: Per spec 94.39, do NOT create default admin user with fixed password here.
    # System initialization flow should be implemented separately.
    # The permissions table is seeded above for RBAC to work once a tenant is created.


def downgrade() -> None:
    op.drop_table('relationships')
    op.drop_table('property_values')
    op.drop_table('property_definitions')
    op.drop_table('assets')
    op.drop_table('entities')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
