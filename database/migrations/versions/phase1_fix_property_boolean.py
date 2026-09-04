"""Task 1.5: Fix PropertyDefinition boolean columns

This migration corrects the required and writable columns in property_definitions
from VARCHAR(32) strings to BOOLEAN type, as originally intended.
"""

import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase1_fix_property_boolean'
down_revision = 'phase1_identity_core'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix property_definitions.required: VARCHAR -> BOOLEAN
    op.alter_column('property_definitions', 'required',
                    existing_type=sa.String(length=32),
                    type_=sa.Boolean(),
                    existing_nullable=False,
                    server_default=sa.text('false'))
    
    # Fix property_definitions.writable: VARCHAR -> BOOLEAN
    op.alter_column('property_definitions', 'writable',
                    existing_type=sa.String(length=32),
                    type_=sa.Boolean(),
                    existing_nullable=False,
                    server_default=sa.text('false'))


def downgrade() -> None:
    # Revert required back to VARCHAR
    op.alter_column('property_definitions', 'required',
                    existing_type=sa.Boolean(),
                    type_=sa.String(length=32),
                    existing_nullable=False,
                    server_default=sa.text("'false'"))
    
    # Revert writable back to VARCHAR
    op.alter_column('property_definitions', 'writable',
                    existing_type=sa.Boolean(),
                    type_=sa.String(length=32),
                    existing_nullable=False,
                    server_default=sa.text("'false'"))
