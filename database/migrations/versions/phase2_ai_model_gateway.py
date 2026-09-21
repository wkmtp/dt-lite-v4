"""Phase 2 AI Model Gateway — model_providers, model_configs, tenant_quotas, ai_usage_logs, ai_audit_logs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase2_ai_model_gateway"
down_revision = "phase2_ai_orchestrator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("api_key_ref", sa.String(255), nullable=True),
        sa.Column("models", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_provider_name"),
    )

    op.create_table(
        "model_configs",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("provider_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("primary_model", sa.String(100), nullable=False),
        sa.Column("fallback_models", postgresql.JSONB(), nullable=True),
        sa.Column("routing_strategy", sa.String(50), nullable=False, server_default="round_robin"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_model_config"),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"]),
    )

    op.create_table(
        "tenant_quotas",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("rpm_limit", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("tpm_limit", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("daily_budget_usd", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("monthly_budget_usd", sa.Float(), nullable=False, server_default="200.0"),
        sa.Column("daily_spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("monthly_spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_reset_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_quota"),
    )

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("trace_id", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_usage_tenant_created", "ai_usage_logs", ["tenant_id", "created_at"]),
        sa.Index("ix_usage_trace", "ai_usage_logs", ["trace_id"]),
        sa.Index("ix_usage_model", "ai_usage_logs", ["model", "created_at"]),
    )

    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("trace_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_audit_tenant_action", "ai_audit_logs", ["tenant_id", "action", "created_at"]),
        sa.Index("ix_audit_trace", "ai_audit_logs", ["trace_id"]),
    )


def downgrade() -> None:
    op.drop_index("ix_audit_trace", table_name="ai_audit_logs")
    op.drop_index("ix_audit_tenant_action", table_name="ai_audit_logs")
    op.drop_table("ai_audit_logs")
    op.drop_index("ix_usage_model", table_name="ai_usage_logs")
    op.drop_index("ix_usage_trace", table_name="ai_usage_logs")
    op.drop_index("ix_usage_tenant_created", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_table("tenant_quotas")
    op.drop_table("model_configs")
    op.drop_table("model_providers")
