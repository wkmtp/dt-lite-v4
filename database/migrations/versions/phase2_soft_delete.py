"""Task 2: Add Soft Delete Fields to Core Tables

This migration adds deleted_at column to core tables to support soft delete functionality.
Tables affected:
- entities
- assets  
- property_definitions
- relationships
- users (identity)

Note: tenant, roles, permissions tables do NOT get deleted_at as they are system-level.
"""

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase2_soft_delete'
down_revision = 'phase1_fix_property_boolean'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deleted_at to core tables
    op.add_column('entities', sa.Column('deleted_at', sapg.TIMESTAMPTZ(), nullable=True))
    op.add_column('assets', sa.Column('deleted_at', sapg.TIMESTAMPTZ(), nullable=True))
    op.add_column('property_definitions', sa.Column('deleted_at', sapg.TIMESTAMPTZ(), nullable=True))
    op.add_column('relationships', sa.Column('deleted_at', sapg.TIMESTAMPTZ(), nullable=True))
    op.add_column('users', sa.Column('deleted_at', sapg.TIMESTAMPTZ(), nullable=True))
    
    # Add indexes for soft delete filtering
    op.create_index('idx_entities_deleted', 'entities', ['deleted_at'], 
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_assets_deleted', 'assets', ['deleted_at'],
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_property_defs_deleted', 'property_definitions', ['deleted_at'],
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_relationships_deleted', 'relationships', ['deleted_at'],
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_deleted', 'users', ['deleted_at'],
                    postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    # Remove columns and indexes
    op.drop_index('idx_users_deleted', 'users')
    op.drop_index('idx_relationships_deleted', 'relationships')
    op.drop_index('idx_property_defs_deleted', 'property_definitions')
    op.drop_index('idx_assets_deleted', 'assets')
    op.drop_index('idx_entities_deleted', 'entities')
    
    op.drop_column('users', 'deleted_at')
    op.drop_column('relationships', 'deleted_at')
    op.drop_column('property_definitions', 'deleted_at')
    op.drop_column('assets', 'deleted_at')
    op.drop_column('entities', 'deleted_at')
