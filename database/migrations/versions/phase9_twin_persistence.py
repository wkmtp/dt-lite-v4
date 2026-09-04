"""Task 9 Migration: Twin Persistence Foundation

Creates tables:
- twin_definitions: Type definitions for twins
- twin_entities: Persistent twin instances
- twin_bindings: Device-Twin relationships

This migration extends the runtime foundation (Task 8) with persistence.
"""
import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase9_twin_persistence'
down_revision = 'phase6_telemetry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twin Definitions table - stores type/schema definitions
    op.create_table(
        'twin_definitions',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512)),
        sa.Column('schema', sapg.JSONB(), nullable=False, server_default="{}"),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default="{}"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    op.create_index('ix_twin_def_tenant_code', 'twin_definitions', ['tenant_id', 'code'])
    op.create_unique_constraint('uq_twin_def_tenant_code', 'twin_definitions', ['tenant_id', 'code'])

    # Twin Entities table - persistent twin instances
    op.create_table(
        'twin_entities',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('definition_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(length=256), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default="{}"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['definition_id'], ['twin_definitions.id']),
    )
    op.create_index('ix_twin_ent_tenant_external', 'twin_entities', ['tenant_id', 'external_id'])
    op.create_index('ix_twin_ent_definition', 'twin_entities', ['definition_id'])

    # Twin Bindings table - decoupled device-twin relationship
    op.create_table(
        'twin_bindings',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('twin_entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('binding_type', sa.String(length=32), nullable=False,
                  server_default="'mirror'"),
        sa.Column('metadata', sapg.JSONB(), nullable=False, server_default="{}"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['twin_entity_id'], ['twin_entities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_twin_bind_device', 'twin_bindings', ['device_id'])
    op.create_index('ix_twin_bind_entity', 'twin_bindings', ['twin_entity_id'])
    op.create_index('ix_twin_bind_tenant_device', 'twin_bindings', ['tenant_id', 'device_id'])


def downgrade() -> None:
    op.drop_table('twin_bindings')
    op.drop_table('twin_entities')
    op.drop_table('twin_definitions')
