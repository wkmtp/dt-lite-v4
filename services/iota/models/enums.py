"""Data Acquisition Enums - Protocol-independent type definitions."""
from enum import Enum


class DataType(str, Enum):
    """Supported data types for DataPoints."""
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"


class AccessMode(str, Enum):
    """Access mode for DataPoints."""
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
    """Sampling mode for DataPoints."""
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
    """Adapter capabilities declaration."""
    READ = "READ"
    WRITE = "WRITE"
    DISCOVERY = "DISCOVERY"
    SUBSCRIBE = "SUBSCRIBE"
