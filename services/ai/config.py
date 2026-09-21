"""AI Service Configuration using Pydantic Settings.

All model endpoints, embedding config, RAG parameters,
and orchestration settings are loaded from environment variables
to avoid hardcoding.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class AIConfig(BaseSettings):
    """Configuration for the AI Agent runtime layer."""

    # ------------------------------------------------------------------
    # Model Endpoints (vendor-agnostic via ModelGateway)
    # ------------------------------------------------------------------
    LLM_PROVIDER: Literal["openai", "anthropic", "local"] = "openai"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL_NAME: str = "gpt-4o"
    LLM_API_KEY_ENV_VAR: str = "LLM_API_KEY"

    # Anthropic-specific
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL_NAME: str = "claude-3-opus-20240229"
    ANTHROPIC_API_KEY_ENV_VAR: str = "ANTHROPIC_API_KEY"

    # ------------------------------------------------------------------
    # Embedding Configuration
    # ------------------------------------------------------------------
    EMBEDDING_PROVIDER: Literal["openai", "local"] = "openai"
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_API_KEY_ENV_VAR: str = "EMBEDDING_API_KEY"

    # ------------------------------------------------------------------
    # RAG Parameters
    # ------------------------------------------------------------------
    RAG_TOP_K: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    RAG_SCORE_THRESHOLD: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum similarity score")
    RAG_CHUNK_SIZE: int = Field(default=512, ge=64, le=2048, description="Chunk size in tokens")
    RAG_CHUNK_OVERLAP: int = Field(default=64, ge=0, le=256, description="Chunk overlap in tokens")
    RAG_VECTOR_STORE_PATH: Path = Field(
        default=Path("data/vector_store"),
        description="Path to local vector store (for local mode)",
    )

    # ------------------------------------------------------------------
    # Agent Orchestration Settings
    # ------------------------------------------------------------------
    AGENT_MAX_ITERATIONS: int = Field(default=10, ge=1, le=50, description="Max ReAct loop iterations")
    AGENT_TIMEOUT_SECONDS: int = Field(default=120, ge=10, le=600, description="Per-iteration timeout")
    AGENT_MEMORY_WINDOW_TOKENS: int = Field(default=32_000, ge=1_000, description="Short-term memory window")
    AGENT_ENABLE_STREAMING: bool = Field(default=True, description="Enable SSE streaming responses")
    AGENT_TOOL_REGISTRY_DIR: Path = Field(
        default=Path("services/ai/tools"),
        description="Directory for hot-reloadable tool definitions",
    )

    # ------------------------------------------------------------------
    # Service URLs (for cross-service calls via ModelGateway)
    # ------------------------------------------------------------------
    GATEWAY_URL: str = Field(
        default="http://localhost:8000",
        description="DT-Lite API Gateway base URL",
    )
    CORE_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Core service base URL",
    )
    TELEMETRY_SERVICE_URL: str = Field(
        default="http://localhost:8004",
        description="Telemetry service base URL",
    )
    ONTOLOGY_SERVICE_URL: str = Field(
        default="http://localhost:8003",
        description="Ontology service base URL",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Module-level singleton
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """Return the global AIConfig singleton, creating it if necessary."""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig()
    return _ai_config
