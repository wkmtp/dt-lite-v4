"""Environment-based Secret Provider - Contract implementation."""
import os
from typing import Optional

from services.iota.contracts import SecretProvider


class EnvironmentSecretProvider(SecretProvider):
    """Stores secrets in environment variables.

    This is a minimal implementation for Task 5.
    Production should use Vault/KMS/encrypted config.

    Note: endpoint is NOT stored here. Only actual credentials
    (passwords, tokens, API keys) should be stored.
    """

    def __init__(self, prefix: str = "DTLITE_SECRET_"):
        self._prefix = prefix

    async def get_secret(self, ref: str) -> Optional[str]:
        env_key = f"{self._prefix}{ref.upper().replace('-', '_')}"
        return os.getenv(env_key)

    async def store_secret(self, ref: str, value: str) -> None:
        # In production, this would store in Vault/KMS
        # For now, we just validate it's not empty
        if not ref or not value:
            raise ValueError("Invalid secret reference or value")

    async def delete_secret(self, ref: str) -> None:
        """Delete a secret from environment."""
        env_key = f"{self._prefix}{ref.upper().replace('-', '_')}"
        if env_key in os.environ:
            del os.environ[env_key]
        else:
            raise ValueError(f"Secret not found: {ref}")
