"""Data Acquisition Contracts - Protocol-Independent Interface Definitions."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class DataType(str, Enum):
    """Supported normalized telemetry data types."""
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"


class AccessMode(str, Enum):
    """DataPoint access mode."""
    READ = "READ"
    WRITE = "WRITE"
    READ_WRITE = "READ_WRITE"

    @property
    def can_read(self) -> bool:
        return self in (AccessMode.READ, AccessMode.READ_WRITE)

    @property
    def can_write(self) -> bool:
        return self in (AccessMode.WRITE, AccessMode.READ_WRITE)


class SamplingMode(str, Enum):
    """DataPoint sampling mode."""
    POLL = "POLL"
    SUBSCRIBE = "SUBSCRIBE"
    ON_CHANGE = "ON_CHANGE"
    MANUAL = "MANUAL"


class DataQuality(str, Enum):
    """Data quality indicator."""
    GOOD = "GOOD"
    BAD = "BAD"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"


class AdapterCapability(str, Enum):
    """Adapter declared capabilities."""
    READ = "READ"
    WRITE = "WRITE"
    DISCOVERY = "DISCOVERY"
    SUBSCRIBE = "SUBSCRIBE"


@dataclass
class DiscoveryResult:
    """Protocol-independent discovery result."""
    external_id: str
    name: str
    discovery_type: str  # "device" or "datapoint"
    device_type: Optional[str] = None
    data_type: Optional[str] = None
    unit: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class NormalizedTelemetry:
    """Normalized telemetry payload from any protocol adapter."""
    tenant_id: str
    device_id: str
    datapoint_id: str

    event_time: datetime
    ingested_at: datetime

    value: Any
    data_type: str
    unit: Optional[str] = None

    quality: str = DataQuality.GOOD.value
    metadata: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if not self.tenant_id:
            errors.append("tenant_id required")
        if not self.device_id:
            errors.append("device_id required")
        if not self.datapoint_id:
            errors.append("datapoint_id required")
        if not self.event_time:
            errors.append("event_time required")
        if not self.ingested_at:
            errors.append("ingested_at required")
        if self.data_type not in {d.value for d in DataType}:
            errors.append(f"invalid data_type: {self.data_type}")
        if self.quality not in {q.value for q in DataQuality}:
            errors.append(f"invalid quality: {self.quality}")
        return errors


class SecretProvider(ABC):
    """Contract for secret/credential lookup.

    Implementations may use environment variables, encrypted config,
    or external Vault/KMS. Business code must depend on this contract,
    never on concrete secret storage.

    Note: endpoint is NOT a secret. Use SecretProvider only for
    actual credential values (passwords, tokens, API keys).
    """

    @abstractmethod
    async def get_secret(self, ref: str) -> Optional[str]:
        """Retrieve a secret by reference key.

        Args:
            ref: The credentials_ref identifier stored in Connection.

        Returns:
            The secret value as a string, or None if not found.
        """
        ...

    @abstractmethod
    async def store_secret(self, ref: str, value: str) -> None:
        """Store a secret by reference key.

        Args:
            ref: The unique identifier for this secret.
            value: The secret value to store.
        """
        ...

    @abstractmethod
    async def delete_secret(self, ref: str) -> None:
        """Delete a secret by reference key.

        Args:
            ref: The secret reference to delete.

        Raises:
            ValueError: If the secret reference is not found.
        """
        ...


class ProtocolAdapter(ABC):
    """Contract that all protocol adapters must implement.

    Task 5 does NOT implement runtime — only the interface.
    Each adapter declares its capabilities via capabilities().
    """

    @abstractmethod
    async def connect(self, endpoint: str, credentials_ref: str, config: dict) -> None:
        """Establish connection to the endpoint."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection."""
        ...

    @abstractmethod
    async def health(self) -> bool:
        """Return True if connection is healthy."""
        ...

    @abstractmethod
    async def discover(self) -> list[DiscoveryResult]:
        """Discover available devices and/or data points."""
        ...

    @abstractmethod
    async def read(self, external_ids: list[str]) -> list[NormalizedTelemetry]:
        """Read values by external IDs."""
        ...

    @abstractmethod
    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        """Write a value to a data point."""
        ...

    @abstractmethod
    async def subscribe(
        self, external_id: str, callback: Any
    ) -> str:
        """Subscribe to a data point. Returns subscription ID."""
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a data point."""
        ...

    @abstractmethod
    def capabilities(self) -> set[AdapterCapability]:
        """Return the set of capabilities this adapter supports."""
        ...
