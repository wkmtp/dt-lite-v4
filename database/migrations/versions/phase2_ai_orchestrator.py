"""Phase 2 AI Orchestrator — workflows, workflow_versions, workflow_executions, workflow_approvals."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase2_ai_orchestrator"
down_revision = "phase2_ai_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dsl_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_workflows_tenant_status", "workflows", ["tenant_id", "status"]),
    )

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("workflow_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("dsl_json", postgresql.JSONB(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow_id", "version_number", name="uq_wf_version"),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("workflow_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("execution_id", sa.String(100), nullable=False),
        sa.Column("input_vars", postgresql.JSONB(), nullable=True),
        sa.Column("output_vars", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("current_node_id", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_executions_tenant_status", "workflow_executions", ["tenant_id", "status"]),
        sa.Index("ix_executions_workflow", "workflow_executions", ["workflow_id", "started_at"]),
    )

    op.create_table(
        "workflow_step_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("execution_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("compensation_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.Index("ix_step_logs_execution", "workflow_step_logs", ["execution_id"]),
    )

    op.create_table(
        "workflow_approvals",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("execution_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("requested_by", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("approved_by", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_approvals_execution", "workflow_approvals", ["execution_id"]),
    )


def downgrade() -> None:
    op.drop_index("ix_approvals_execution", table_name="workflow_approvals")
    op.drop_table("workflow_approvals")
    op.drop_index("ix_step_logs_execution", table_name="workflow_step_logs")
    op.drop_table("workflow_step_logs")
    op.drop_index("ix_executions_workflow", table_name="workflow_executions")
    op.drop_index("ix_executions_tenant_status", table_name="workflow_executions")
    op.drop_table("workflow_executions")
    op.drop_table("workflow_versions")
    op.drop_index("ix_workflows_tenant_status", table_name="workflows")
    op.drop_table("workflows")
