"""PartitionRouter — Consistent-hash based partition routing for telemetry."""
import hashlib
import logging

logger = logging.getLogger(__name__)


class PartitionRouter:
    """Routes telemetry points to partitions using consistent hashing on asset_id.

    Supports N partitions for horizontal scaling of TimescaleDB hypertables.
    """

    def __init__(self, num_partitions: int = 4):
        self._num_partitions = num_partitions
        self._hash_ring: list[str] = []
        self._build_hash_ring()

    def _build_hash_ring(self) -> None:
        """Build consistent hash ring with 10 virtual nodes per partition."""
        self._hash_ring = sorted(
            hashlib.md5(f"partition-{i}".encode()).hexdigest()
            for i in range(self._num_partitions * 10)
        )

    def get_partition(self, asset_id) -> int:
        """Get partition index for an asset_id using consistent hashing."""
        key = hashlib.md5(str(asset_id).encode()).hexdigest()
        for i, ring_key in enumerate(self._hash_ring):
            if key <= ring_key:
                return i % self._num_partitions
        return 0

    def get_partitions(self, asset_ids: list) -> dict:
        """Map asset_ids to partition indices."""
        return {aid: self.get_partition(aid) for aid in asset_ids}

    @property
    def num_partitions(self) -> int:
        return self._num_partitions
