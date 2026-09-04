"""Phase 1 Migration: Data Acquisition Domain (Task 5)

Creates tables for:
- data_sources
- connections
- devices
- data_points
- device_entity_bindings
"""
import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase5_data_acquisition'
down_revision = 'phase2_soft_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # data_sources
    op.create_table('data_sources',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512)),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='inactive'),
        sa.Column('config', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_datasource_tenant_name'),
    )
    op.create_index('ix_datasource_tenant_status', 'data_sources', ['tenant_id', 'status'])

    # connections
    op.create_table('connections',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('endpoint', sa.String(length=512), nullable=False),
        sa.Column('credentials_ref', sa.String(length=256), nullable=False),
        sa.Column('timeout', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('retry_policy', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='disconnected'),
        sa.Column('config', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_connection_tenant_name'),
    )
    op.create_index('ix_connection_datasource', 'connections', ['data_source_id'])

    # devices
    op.create_table('devices',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', sapg.UUID(as_uuid=True), nullable=True),
        sa.Column('connection_id', sapg.UUID(as_uuid=True), nullable=True),
        sa.Column('external_id', sa.String(length=256), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='offline'),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'external_id', name='uq_device_tenant_external'),
    )
    op.create_index('ix_device_datasource', 'devices', ['data_source_id'])
    op.create_index('ix_device_connection', 'devices', ['connection_id'])

    # data_points
    op.create_table('data_points',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(length=256), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=32)),
        sa.Column('access_mode', sa.String(length=32), nullable=False),
        sa.Column('sampling_mode', sa.String(length=32), nullable=False),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'device_id', 'key', name='uq_datapoint_tenant_device_key'),
    )
    op.create_index('ix_datapoint_external', 'data_points', ['external_id'])

    # device_entity_bindings
    op.create_table('device_entity_bindings',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('binding_type', sa.String(length=64), nullable=False),
        sa.Column('extra_data', sapg.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('device_id', 'entity_id', name='uq_binding_device_entity'),
    )


def downgrade() -> None:
    op.drop_table('device_entity_bindings')
    op.drop_table('data_points')
    op.drop_table('devices')
    op.drop_table('connections')
    op.drop_table('data_sources')
