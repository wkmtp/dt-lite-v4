"""Phase 2 AI Indexes — vector indexes, full-text indexes, composite index optimization."""
from alembic import op
import sqlalchemy as sa

revision = "phase2_ai_indexes"
down_revision = "phase2_ai_model_gateway"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Agent memories — vector similarity search index
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_memories_embedding_cosine "
        "ON agent_memories USING ivfflat (embedding_vector vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # Document chunks — full-text search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_doc_chunks_content_gin "
        "ON document_chunks USING gin(to_tsvector('english', content))"
    )

    # Embeddings — vector similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_cosine "
        "ON embeddings USING ivfflat (embedding_vector vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # Usage logs — time-range queries for cost tracking
    op.create_index(
        "ix_usage_date_range", "ai_usage_logs",
        [sa.text("tenant_id"), sa.text("created_at DESC")]
    )

    # Audit logs — time-range queries
    op.create_index(
        "ix_audit_date_range", "ai_audit_logs",
        [sa.text("tenant_id"), sa.text("created_at DESC")]
    )

    # Workflow executions — active execution lookup
    op.create_index(
        "ix_wf_exec_active", "workflow_executions",
        ["status", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_wf_exec_active", table_name="workflow_executions")
    op.drop_index("ix_audit_date_range", table_name="ai_audit_logs")
    op.drop_index("ix_usage_date_range", table_name="ai_usage_logs")
    op.drop_index("ix_embeddings_vector_cosine", table_name="embeddings")
    op.drop_index("ix_doc_chunks_content_gin", table_name="document_chunks")
    op.drop_index("ix_agent_memories_embedding_cosine", table_name="agent_memories")
    # Note: extension drop requires superuser, skipped in downgrade
