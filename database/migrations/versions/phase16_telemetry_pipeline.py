"""Phase 16 Migration: Telemetry Pipeline Enhancement.

Creates tables and views for high-throughput telemetry ingestion,
continuous aggregates, and data quality tracking.
"""
from alembic import op
import sqlalchemy as sa

revision = 'phase16_telemetry_pipeline'
down_revision = 'phase14_twin_activation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # telemetry_quality table
    op.create_table(
        'telemetry_quality',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('point_id', sa.UUID(), nullable=False),
        sa.Column('completeness', sa.Float(), nullable=False, default=100.0),
        sa.Column('timeliness', sa.Float(), nullable=False, default=100.0),
        sa.Column('validity', sa.Float(), nullable=False, default=100.0),
        sa.Column('consistency', sa.Float(), nullable=False, default=100.0),
        sa.Column('accuracy', sa.Float(), nullable=False, default=100.0),
        sa.Column('overall', sa.Float(), nullable=False),
        sa.Column('quality_level', sa.String(32), nullable=False, default='GOOD'),
        sa.Column('rules_triggered', sa.JSON(), nullable=True),
        sa.Column('marked_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['point_id'], ['telemetry_points.id'],
                               ondelete='CASCADE'),
    )
    op.create_index('ix_quality_point', 'telemetry_quality', ['point_id'])
    op.create_index('ix_quality_tenant_level', 'telemetry_quality',
                    ['tenant_id', 'quality_level'])

    # telemetry_config table (for configurable retention/compression)
    op.create_table(
        'telemetry_config',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('config_key', sa.String(128), nullable=False),
        sa.Column('config_value', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'config_key'),
    )
    op.create_index('ix_telemetry_config_tenant', 'telemetry_config', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_telemetry_config_tenant', table_name='telemetry_config')
    op.drop_table('telemetry_config')
    op.drop_index('ix_quality_tenant_level', table_name='telemetry_quality')
    op.drop_index('ix_quality_point', table_name='telemetry_quality')
    op.drop_table('telemetry_quality')
