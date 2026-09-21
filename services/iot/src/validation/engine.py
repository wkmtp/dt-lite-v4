"""Validation Engine — Round-trip read/write + data quality scoring."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DataQualityScore:
    """Composite data quality score."""
    completeness: float  # 0.0 - 1.0
    timeliness: float    # 0.0 - 1.0
    validity: float      # 0.0 - 1.0
    composite: float     # weighted average


class ValidationEngine:
    """
    Validation Engine: round-trip read/write test + data quality scoring.
    """

    def round_trip_test(
        self,
        write_value: float,
        read_value: float,
        tolerance: float = 0.01,
    ) -> tuple[bool, float]:
        """
        Verify round-trip: write → read back.
        Returns (passed, deviation).
        """
        deviation = abs(write_value - read_value)
        passed = deviation <= tolerance
        logger.info("Round-trip test: value=%.4f, read=%.4f, deviation=%.4f, passed=%s",
                     write_value, read_value, deviation, passed)
        return passed, deviation

    def score_completeness(self, expected_fields: int, actual_fields: int) -> float:
        """Completeness: ratio of fields present vs expected."""
        if expected_fields == 0:
            return 1.0
        return min(1.0, actual_fields / expected_fields)

    def score_timeliness(self, age_seconds: float, max_age_seconds: float = 60.0) -> float:
        """Timeliness: 1.0 if fresh, 0.0 if stale."""
        if age_seconds <= 0:
            return 1.0
        return max(0.0, 1.0 - age_seconds / max_age_seconds)

    def score_validity(self, value: float, min_val: float, max_val: float) -> float:
        """Validity: 1.0 if in range, decreasing if out of range."""
        if min_val <= value <= max_val:
            return 1.0
        # Partial credit for being close
        range_size = max_val - min_val
        if range_size == 0:
            return 0.0
        distance = min(abs(value - min_val), abs(value - max_val))
        return max(0.0, 1.0 - distance / (range_size * 2))

    def compute_quality_score(
        self,
        value: float,
        min_val: float,
        max_val: float,
        age_seconds: float,
        completeness_ratio: float = 1.0,
    ) -> DataQualityScore:
        """Compute composite data quality score."""
        completeness = completeness_ratio
        timeliness = self.score_timeliness(age_seconds)
        validity = self.score_validity(value, min_val, max_val)
        # Weighted average: validity 40%, completeness 30%, timeliness 30%
        composite = validity * 0.4 + completeness * 0.3 + timeliness * 0.3
        return DataQualityScore(
            completeness=completeness,
            timeliness=timeliness,
            validity=validity,
            composite=round(composite, 4),
        )
