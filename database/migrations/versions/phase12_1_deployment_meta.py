"""Phase 12.1 Migration: Deployment Meta Model Foundation.

Creates tables:
- deployment_profiles: Reusable deployment blueprints
- deployment_instances: Instantiated deployments into operational environments
- deployment_nodes: Logical deployment locations/objects
- deployment_node_capabilities: Capability bindings to nodes with configuration

Extends phase12_semantic_meta_model with deployment meta model layer.
Deployment is NOT Device - it represents semantic instantiation.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase12_1_deployment_meta'
down_revision = 'phase12_semantic_meta_model'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # deployment_profiles table
    op.create_table(
        'deployment_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=64), nullable=False,
                  server_default='general'),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['template_id'], ['twin_templates.id'],
                               ondelete='RESTRICT'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_profile_tenant_name'),
    )
    op.create_index('ix_profile_name', 'deployment_profiles', ['name'])
    op.create_index('ix_profile_tenant', 'deployment_profiles', ['tenant_id'])
    op.create_index('ix_profile_template', 'deployment_profiles', ['template_id'])

    # deployment_instances table
    op.create_table(
        'deployment_instances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['profile_id'], ['deployment_profiles.id'],
                               ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_instance_tenant_name'),
        sa.CheckConstraint(
            "status IN ('draft', 'validating', 'ready', 'deployed', "
            "'running', 'offline', 'archived')",
            name='ck_instance_status',
        ),
    )
    op.create_index('ix_instance_name', 'deployment_instances', ['name'])
    op.create_index('ix_instance_tenant', 'deployment_instances', ['tenant_id'])
    op.create_index('ix_instance_profile', 'deployment_instances', ['profile_id'])

    # deployment_nodes table
    op.create_table(
        'deployment_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('deployment_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('node_type', sa.String(length=128), nullable=False,
                  server_default='generic'),
        sa.Column('entity_type_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployment_instances.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_type_id'], ['entity_type_definitions.id'],
                               ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'deployment_id', 'name',
                            name='uq_node_tenant_deploy_name'),
    )
    op.create_index('ix_node_deployment', 'deployment_nodes', ['deployment_id'])
    op.create_index('ix_node_tenant', 'deployment_nodes', ['tenant_id'])
    op.create_index('ix_node_entity_type', 'deployment_nodes', ['entity_type_id'])

    # deployment_node_capabilities table
    op.create_table(
        'deployment_node_capabilities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('node_id', sa.UUID(), nullable=False),
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('configuration_schema', sa.JSON(), nullable=False,
                  server_default='{}'),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['node_id'], ['deployment_nodes.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capability_id'], ['capability_definitions.id'],
                               ondelete='CASCADE'),
        sa.UniqueConstraint('node_id', 'capability_id', name='uq_node_capability'),
    )
    op.create_index('ix_node_cap_node', 'deployment_node_capabilities', ['node_id'])
    op.create_index('ix_node_cap_capability', 'deployment_node_capabilities',
                    ['capability_id'])
    op.create_index('ix_node_cap_tenant', 'deployment_node_capabilities',
                    ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_node_cap_tenant', table_name='deployment_node_capabilities')
    op.drop_index('ix_node_cap_capability', table_name='deployment_node_capabilities')
    op.drop_index('ix_node_cap_node', table_name='deployment_node_capabilities')
    op.drop_table('deployment_node_capabilities')
    op.drop_index('ix_node_entity_type', table_name='deployment_nodes')
    op.drop_index('ix_node_tenant', table_name='deployment_nodes')
    op.drop_index('ix_node_deployment', table_name='deployment_nodes')
    op.drop_table('deployment_nodes')
    op.drop_index('ix_instance_profile', table_name='deployment_instances')
    op.drop_index('ix_instance_tenant', table_name='deployment_instances')
    op.drop_index('ix_instance_name', table_name='deployment_instances')
    op.drop_table('deployment_instances')
    op.drop_index('ix_profile_template', table_name='deployment_profiles')
    op.drop_index('ix_profile_tenant', table_name='deployment_profiles')
    op.drop_index('ix_profile_name', table_name='deployment_profiles')
    op.drop_table('deployment_profiles')
