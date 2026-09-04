"""Phase 12 Migration: Semantic Ontology + Capability + Template Meta Model Foundation.

Creates tables:
- ontology_concepts: Hierarchical semantic classification
- entity_type_definitions: "What kind of twin can be generated"
- capability_definitions: Reusable ability models
- semantic_properties: Standard data meanings within capabilities
- capability_property_bindings: Junction for capability↔property
- template_capability_bindings: Link templates to required capabilities

Extends phase11_template_foundation with semantic meta model layer.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase12_semantic_meta_model'
down_revision = 'phase11_template_foundation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ontology_concepts table
    op.create_table(
        'ontology_concepts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='general'),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=32), nullable=False, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['ontology_concepts.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_concept_tenant_code'),
    )
    op.create_index('ix_ontology_code', 'ontology_concepts', ['code'])
    op.create_index('ix_ontology_tenant', 'ontology_concepts', ['tenant_id'])
    op.create_index('ix_ontology_parent', 'ontology_concepts', ['parent_id'])

    # entity_type_definitions table
    op.create_table(
        'entity_type_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('ontology_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=64), nullable=True),
        sa.Column('property_schema', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('allowed_capabilities', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['ontology_id'], ['ontology_concepts.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_etype_tenant_code'),
    )
    op.create_index('ix_etype_code', 'entity_type_definitions', ['code'])
    op.create_index('ix_etype_tenant', 'entity_type_definitions', ['tenant_id'])
    op.create_index('ix_etype_ontology', 'entity_type_definitions', ['ontology_id'])

    # capability_definitions table
    op.create_table(
        'capability_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema_definition', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('version', sa.String(length=32), nullable=False, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_capability_tenant_code'),
    )
    op.create_index('ix_capability_code', 'capability_definitions', ['code'])
    op.create_index('ix_capability_tenant', 'capability_definitions', ['tenant_id'])

    # semantic_properties table
    op.create_table(
        'semantic_properties',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['capability_id'], ['capability_definitions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('capability_id', 'name', name='uq_prop_capability_name'),
    )
    op.create_index('ix_prop_capability', 'semantic_properties', ['capability_id'])

    # capability_property_bindings (junction)
    op.create_table(
        'capability_property_bindings',
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('property_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('capability_id', 'property_id'),
        sa.ForeignKeyConstraint(['capability_id'], ['capability_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['semantic_properties.id'], ondelete='CASCADE'),
    )

    # template_capability_bindings table
    op.create_table(
        'template_capability_bindings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['twin_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capability_id'], ['capability_definitions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('template_id', 'capability_id', name='uq_tpc_template_capability'),
    )
    op.create_index('ix_tpc_template', 'template_capability_bindings', ['template_id'])
    op.create_index('ix_tpc_capability', 'template_capability_bindings', ['capability_id'])


def downgrade() -> None:
    op.drop_index('ix_tpc_capability', table_name='template_capability_bindings')
    op.drop_index('ix_tpc_template', table_name='template_capability_bindings')
    op.drop_table('template_capability_bindings')
    op.drop_table('capability_property_bindings')
    op.drop_index('ix_prop_capability', table_name='semantic_properties')
    op.drop_table('semantic_properties')
    op.drop_index('ix_capability_tenant', table_name='capability_definitions')
    op.drop_index('ix_capability_code', table_name='capability_definitions')
    op.drop_table('capability_definitions')
    op.drop_index('ix_etype_ontology', table_name='entity_type_definitions')
    op.drop_index('ix_etype_tenant', table_name='entity_type_definitions')
    op.drop_index('ix_etype_code', table_name='entity_type_definitions')
    op.drop_table('entity_type_definitions')
    op.drop_index('ix_ontology_parent', table_name='ontology_concepts')
    op.drop_index('ix_ontology_tenant', table_name='ontology_concepts')
    op.drop_index('ix_ontology_code', table_name='ontology_concepts')
    op.drop_table('ontology_concepts')