"""Phase 2 AI Agent Runtime — agent_sessions, agent_messages, agent_memories, agent_tool_calls."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "phase2_ai_agent_runtime"
down_revision = "phase16_telemetry_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("model", sa.String(100), nullable=False, server_default="gpt-4o"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_agent_session_tenant"),
    )
    op.create_index("ix_agent_sessions_tenant_created", "agent_sessions", ["tenant_id", "created_at"])

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("session_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_results", postgresql.JSONB(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_messages_session", "agent_messages", ["session_id"])
    op.create_index("ix_agent_messages_tenant", "agent_messages", ["tenant_id", "created_at"])

    op.create_table(
        "agent_memories",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column("memory_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_agent_memories_tenant_type", "agent_memories", ["tenant_id", "memory_type"]),
        sa.Index("ix_agent_memories_embedding", "agent_memories", using="gin",
                 postgresql_using="GIN (embedding vector_cosine_op)"),
    )

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("session_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("message_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_input", postgresql.JSONB(), nullable=False),
        sa.Column("tool_output", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_tool_calls_session", "agent_tool_calls", ["session_id"])
    op.create_index("ix_agent_tool_calls_tenant", "agent_tool_calls", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_tool_calls_tenant", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_session", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")
    op.drop_index("ix_agent_memories_embedding", table_name="agent_memories")
    op.drop_index("ix_agent_memories_tenant_type", table_name="agent_memories")
    op.drop_table("agent_memories")
    op.drop_index("ix_agent_messages_tenant", table_name="agent_messages")
    op.drop_index("ix_agent_messages_session", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_sessions_tenant_created", table_name="agent_sessions")
    op.drop_table("agent_sessions")
