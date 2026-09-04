"""Phase 13 Migration: Provisioning Engine Foundation.

Creates tables:
- provisioning_plans: Planning results before execution
- provisioning_items: Individual creation actions (CREATE_ENTITY, CREATE_RELATIONSHIP)
- provisioning_executions: Execution records with timestamps

Extends phase12_1_deployment_meta with provisioning layer.
Provisioning converts DeploymentInstance + Template → TwinEntity + TwinRelationship.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase13_provisioning'
down_revision = 'phase12_1_deployment_meta'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # provisioning_plans table
    op.create_table(
        'provisioning_plans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('deployment_instance_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='draft'),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['deployment_instance_id'], ['deployment_instances.id'],
                               ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'deployment_instance_id', name='uq_plan_deployment'),
    )
    op.create_index('ix_plan_tenant', 'provisioning_plans', ['tenant_id'])
    op.create_index('ix_plan_deployment', 'provisioning_plans', ['deployment_instance_id'])

    # provisioning_items table
    op.create_table(
        'provisioning_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('entity_type_id', sa.UUID(), nullable=True),
        sa.Column('external_id', sa.String(length=256), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False,
                  server_default='CREATE_ENTITY'),
        sa.Column('source_external_id', sa.String(length=256), nullable=True),
        sa.Column('target_external_id', sa.String(length=256), nullable=True),
        sa.Column('rel_type', sa.String(length=64), nullable=True),
        sa.Column('source_twin_id', sa.UUID(), nullable=True),
        sa.Column('target_twin_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='pending'),
        sa.Column('created_twin_id', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['provisioning_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['twin_templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entity_type_id'], ['entity_type_definitions.id'],
                               ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_twin_id'], ['twin_entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_twin_id'], ['twin_entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_twin_id'], ['twin_entities.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('plan_id', 'external_id', 'action',
                            name='uq_item_plan_external_action'),
    )
    op.create_index('ix_item_plan', 'provisioning_items', ['plan_id'])
    op.create_index('ix_item_external', 'provisioning_items', ['external_id'])
    op.create_index('ix_item_tenant', 'provisioning_items', ['tenant_id'])

    # provisioning_executions table
    op.create_table(
        'provisioning_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='started'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('items_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['provisioning_plans.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_execution_plan', 'provisioning_executions', ['plan_id'])
    op.create_index('ix_execution_tenant', 'provisioning_executions', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_execution_tenant', table_name='provisioning_executions')
    op.drop_index('ix_execution_plan', table_name='provisioning_executions')
    op.drop_table('provisioning_executions')
    op.drop_index('ix_item_tenant', table_name='provisioning_items')
    op.drop_index('ix_item_external', table_name='provisioning_items')
    op.drop_index('ix_item_plan', table_name='provisioning_items')
    op.drop_table('provisioning_items')
    op.drop_index('ix_plan_deployment', table_name='provisioning_plans')
    op.drop_index('ix_plan_tenant', table_name='provisioning_plans')
    op.drop_table('provisioning_plans')
