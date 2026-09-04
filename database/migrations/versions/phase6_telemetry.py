"""Phase 6 Migration: Telemetry Time-Series Storage (Task 7)

Creates table:
- telemetry_points

This is append-only historical data with no soft delete.
Indexes optimized for time-range queries by tenant+device and tenant+time.
"""
import sqlalchemy as sa
from alembic import op
import sqlalchemy.dialects.postgresql as sapg

revision = 'phase6_telemetry'
down_revision = 'phase5_data_acquisition'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'telemetry_points',
        sa.Column('id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('datapoint_id', sapg.UUID(as_uuid=True), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('value', sapg.JSONB(), nullable=False),
        sa.Column('data_type', sa.String(length=32), nullable=False),
        sa.Column('unit', sa.String(length=64)),
        sa.Column('quality', sa.String(length=32), nullable=False,
                  server_default="'GOOD'"),
        sa.Column('metadata', sapg.JSONB(), nullable=False,
                  server_default="{}"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['datapoint_id'], ['data_points.id'], ondelete='CASCADE'),
    )

    # Composite index for device-based time-range queries
    op.create_index(
        'ix_telemetry_tenant_device_time',
        'telemetry_points',
        ['tenant_id', 'device_id', 'event_time']
    )

    # Index for datapoint-based queries
    op.create_index(
        'ix_telemetry_datapoint_time',
        'telemetry_points',
        ['datapoint_id', 'event_time']
    )

    # Index for tenant-wide time-range scans
    op.create_index(
        'ix_telemetry_tenant_time',
        'telemetry_points',
        ['tenant_id', 'event_time']
    )


def downgrade() -> None:
    op.drop_index('ix_telemetry_tenant_time', table_name='telemetry_points')
    op.drop_index('ix_telemetry_datapoint_time', table_name='telemetry_points')
    op.drop_index('ix_telemetry_tenant_device_time', table_name='telemetry_points')
    op.drop_table('telemetry_points')
