"""Quality Engine — Five-dimension telemetry data quality scoring."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class QualityLevel(str, Enum):
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"


@dataclass
class QualityScore:
    """Five-dimension quality score for a telemetry point."""
    completeness: float
    timeliness: float
    validity: float
    consistency: float
    accuracy: float
    overall: float
    level: QualityLevel
    rules_triggered: list[str]

    def to_dict(self) -> dict:
        return {
            "completeness": round(self.completeness, 1),
            "timeliness": round(self.timeliness, 1),
            "validity": round(self.validity, 1),
            "consistency": round(self.consistency, 1),
            "accuracy": round(self.accuracy, 1),
            "overall": round(self.overall, 1),
            "level": self.level.value,
            "rules_triggered": self.rules_triggered,
        }


class QualityEngine:
    """Five-dimension quality scoring engine."""

    WEIGHTS = {
        "completeness": 0.15, "timeliness": 0.20,
        "validity": 0.25, "consistency": 0.20, "accuracy": 0.20,
    }

    def __init__(self, staleness_threshold_seconds: float = 300.0,
                 max_rate_of_change: float = 10.0,
                 valid_range: Optional[tuple[float, float]] = None):
        self._staleness_threshold = staleness_threshold_seconds
        self._max_rate_of_change = max_rate_of_change
        self._valid_range = valid_range
        self._history: dict[str, list[float]] = {}

    def score(self, property_code: str, value, timestamp: datetime,
              expected_min: Optional[float] = None,
              expected_max: Optional[float] = None,
              historical_values: Optional[list[float]] = None) -> QualityScore:
        rules_triggered = []

        # 1. Completeness
        if value is None:
            completeness = 0.0
            rules_triggered.append("missing_value")
        else:
            completeness = 100.0

        # 2. Timeliness
        now = datetime.now(timezone.utc)
        age_seconds = (now - timestamp).total_seconds()
        timeliness = max(0.0, 100.0 * (1.0 - age_seconds / self._staleness_threshold))
        if age_seconds > self._staleness_threshold:
            rules_triggered.append("staleness_exceeded")

        # 3. Validity
        if value is None:
            validity = 0.0
        else:
            min_val = expected_min if expected_min is not None else (self._valid_range[0] if self._valid_range else float("-inf"))
            max_val = expected_max if expected_max is not None else (self._valid_range[1] if self._valid_range else float("inf"))
            if min_val <= value <= max_val:
                validity = 100.0
            else:
                validity = 0.0
                rules_triggered.append("out_of_range")

        # 4. Consistency
        if historical_values and len(historical_values) > 0 and value is not None:
            latest = historical_values[-1]
            rate_of_change = abs(value - latest)
            if rate_of_change <= self._max_rate_of_change:
                consistency = 100.0
            else:
                consistency = max(0.0, 100.0 * (1.0 - rate_of_change / (self._max_rate_of_change * 10)))
                rules_triggered.append("rapid_change")
        else:
            consistency = 100.0

        # 5. Accuracy
        if historical_values and len(historical_values) >= 3 and value is not None:
            sma = sum(historical_values[-3:]) / 3
            accuracy = max(0.0, 100.0 * (1.0 - abs(value - sma) / (abs(sma) + 1e-10)))
        else:
            accuracy = 100.0

        overall = (completeness * self.WEIGHTS["completeness"] +
                   timeliness * self.WEIGHTS["timeliness"] +
                   validity * self.WEIGHTS["validity"] +
                   consistency * self.WEIGHTS["consistency"] +
                   accuracy * self.WEIGHTS["accuracy"])

        if overall >= 80:
            level = QualityLevel.GOOD
        elif overall >= 50:
            level = QualityLevel.UNCERTAIN
        else:
            level = QualityLevel.BAD

        if property_code not in self._history:
            self._history[property_code] = []
        if value is not None:
            self._history[property_code].append(float(value))
        if len(self._history.get(property_code, [])) > 1000:
            self._history[property_code] = self._history[property_code][-1000:]

        return QualityScore(
            completeness=completeness, timeliness=timeliness,
            validity=validity, consistency=consistency, accuracy=accuracy,
            overall=overall, level=level, rules_triggered=rules_triggered,
        )
