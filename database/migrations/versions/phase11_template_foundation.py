"""Phase 11 Migration: Industry Template Foundation.

Creates tables:
- twin_templates: Reusable digital twin type definitions
- template_properties: Attribute definitions within templates
- template_relationships: Allowed semantic relationships at template level

Extends phase10_twin_graph with template-based industry enablement.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase11_template_foundation'
down_revision = 'phase10_twin_graph'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # twin_templates table
    op.create_table(
        'twin_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=64), nullable=False, server_default='general'),
        sa.Column('version', sa.String(length=32), nullable=False, server_default='1.0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema_definition', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_template_tenant_code'),
    )
    op.create_index('ix_template_code', 'twin_templates', ['code'])
    op.create_index('ix_template_tenant', 'twin_templates', ['tenant_id'])

    # template_properties table
    op.create_table(
        'template_properties',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=64), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['twin_templates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('template_id', 'name', name='uq_prop_template_name'),
    )
    op.create_index('ix_prop_template', 'template_properties', ['template_id'])

    # template_relationships table
    op.create_table(
        'template_relationships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=64), nullable=False),
        sa.Column('target_template', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['twin_templates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'template_id', 'relationship_type', 'target_template',
            name='uq_rel_template_type_target',
        ),
    )
    op.create_index('ix_rel_template', 'template_relationships', ['template_id'])


def downgrade() -> None:
    op.drop_index('ix_rel_template', table_name='template_relationships')
    op.drop_table('template_relationships')
    op.drop_index('ix_prop_template', table_name='template_properties')
    op.drop_table('template_properties')
    op.drop_index('ix_template_tenant', table_name='twin_templates')
    op.drop_index('ix_template_code', table_name='twin_templates')
    op.drop_table('twin_templates')
