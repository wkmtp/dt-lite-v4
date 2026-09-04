"""Phase 10 Migration: Twin Graph & Semantic Query Foundation.

Creates table:
- twin_relationships: Semantic connections between persistent twin entities

Extends phase9_twin_persistence with graph topology support.
"""
import sqlalchemy as sa
from alembic import op

revision = 'phase10_twin_graph'
down_revision = 'phase9_twin_persistence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'twin_relationships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('source_twin_id', sa.UUID(), nullable=False),
        sa.Column('target_twin_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=64), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['source_twin_id'], ['twin_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_twin_id'], ['twin_entities.id'], ondelete='CASCADE'),
        sa.CheckConstraint('source_twin_id != target_twin_id', name='ck_no_self_reference'),
    )
    op.create_index('ix_twin_rel_source', 'twin_relationships', ['source_twin_id'])
    op.create_index('ix_twin_rel_target', 'twin_relationships', ['target_twin_id'])
    op.create_index('ix_twin_rel_type', 'twin_relationships', ['relationship_type'])
    op.create_index('ix_twin_rel_tenant', 'twin_relationships', ['tenant_id'])
    op.create_index('ix_twin_rel_all', 'twin_relationships',
                    ['tenant_id', 'source_twin_id', 'target_twin_id', 'relationship_type'])


def downgrade() -> None:
    op.drop_index('ix_twin_rel_all', table_name='twin_relationships')
    op.drop_index('ix_twin_rel_tenant', table_name='twin_relationships')
    op.drop_index('ix_twin_rel_type', table_name='twin_relationships')
    op.drop_index('ix_twin_rel_target', table_name='twin_relationships')
    op.drop_index('ix_twin_rel_source', table_name='twin_relationships')
    op.drop_table('twin_relationships')
