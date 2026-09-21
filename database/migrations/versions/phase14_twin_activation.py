"""Phase 14 Migration: Twin Activation & Operational Binding Foundation.

Creates tables:
- twin_activation_logs: Tracks activation state of PersistentTwinEntity
- twin_commands: Command lifecycle from Twin to physical device

Extends phase13_provisioning with activation and command layers.
Activation transforms provisioned entities into operational runtime twins.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase14_twin_activation'
down_revision = 'phase13_provisioning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # twin_activation_logs table
    op.create_table(
        'twin_activation_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('twin_entity_id', sa.UUID(), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False,
                  server_default='created'),
        sa.Column('binding_id', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['twin_entity_id'], ['twin_entities.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['binding_id'], ['twin_bindings.id'],
                               ondelete='SET NULL'),
    )
    op.create_index('ix_activation_entity', 'twin_activation_logs', ['twin_entity_id'])
    op.create_index('ix_activation_tenant_entity', 'twin_activation_logs',
                    ['tenant_id', 'twin_entity_id'])

    # twin_commands table
    op.create_table(
        'twin_commands',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('twin_binding_id', sa.UUID(), nullable=False),
        sa.Column('target_device_id', sa.UUID(), nullable=False),
        sa.Column('command_type', sa.String(length=32), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='created'),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['twin_binding_id'], ['twin_bindings.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_device_id'], ['devices.id'],
                               ondelete='CASCADE'),
    )
    op.create_index('ix_command_binding', 'twin_commands', ['twin_binding_id'])
    op.create_index('ix_command_device', 'twin_commands', ['target_device_id'])
    op.create_index('ix_command_tenant_status', 'twin_commands',
                    ['tenant_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_command_tenant_status', table_name='twin_commands')
    op.drop_index('ix_command_device', table_name='twin_commands')
    op.drop_index('ix_command_binding', table_name='twin_commands')
    op.drop_table('twin_commands')
    op.drop_index('ix_activation_tenant_entity', table_name='twin_activation_logs')
    op.drop_index('ix_activation_entity', table_name='twin_activation_logs')
    op.drop_table('twin_activation_logs')
