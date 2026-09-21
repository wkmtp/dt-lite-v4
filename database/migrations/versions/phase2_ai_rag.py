"""Phase 2 AI RAG — knowledge_bases, documents, document_chunks, embeddings."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase2_ai_rag"
down_revision = "phase2_ai_agent_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vector_store_type", sa.String(50), nullable=False, server_default="pgvector"),
        sa.Column("embedding_model", sa.String(100), nullable=False, server_default="text-embedding-3-large"),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_kb_tenant_name", "knowledge_bases", ["tenant_id", "name"], unique=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.Index("ix_docs_tenant_status", "documents", ["tenant_id", "status"]),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("document_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.Index("ix_chunks_doc_index", "document_chunks", ["document_id", "chunk_index"]),
        sa.Index("ix_chunks_tenant_kb", "document_chunks", ["tenant_id", "kb_id"]),
    )

    op.create_table(
        "embeddings",
        sa.Column("chunk_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("embedding_vector", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("sparse_vector", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("chunk_id"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.Index("ix_embeddings_tenant_kb", "embeddings", ["tenant_id", "kb_id"]),
    )


def downgrade() -> None:
    op.drop_index("ix_embeddings_tenant_kb", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index("ix_chunks_tenant_kb", table_name="document_chunks")
    op.drop_index("ix_chunks_doc_index", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_docs_tenant_status", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_kb_tenant_name", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
