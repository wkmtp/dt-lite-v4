"""Quality Rules — JSON Schema-based rule definitions."""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityRule:
    """A single quality rule definition."""
    rule_id: str
    name: str
    description: str
    dimension: str  # completeness, timeliness, validity, consistency, accuracy
    condition: dict  # JSON Schema-like condition
    weight: float = 1.0
    enabled: bool = True

    def evaluate(self, value: float, metadata: dict) -> tuple[bool, str]:
        """Evaluate the rule against a value. Returns (passed, reason)."""
        condition = self.condition
        op = condition.get("op", "range")
        min_val = condition.get("min")
        max_val = condition.get("max")
        pattern = condition.get("pattern")

        if op == "range" and min_val is not None and max_val is not None:
            passed = min_val <= value <= max_val
            reason = f"value={value} not in [{min_val}, {max_val}]" if not passed else ""
            return passed, reason
        elif op == "pattern" and pattern:
            import re
            passed = bool(re.match(pattern, str(value)))
            reason = f"value={value} does not match pattern={pattern}" if not passed else ""
            return passed, reason
        return True, ""


class QualityRuleEngine:
    """Evaluates a set of quality rules against telemetry data."""

    DEFAULT_RULES = [
        QualityRule(
            rule_id="temp_range",
            name="Temperature Range",
            description="Temperature must be between -50 and 150 degC",
            dimension="validity",
            condition={"op": "range", "min": -50.0, "max": 150.0},
            weight=1.0,
        ),
        QualityRule(
            rule_id="humid_range",
            name="Humidity Range",
            description="Humidity must be between 0 and 100 percent",
            dimension="validity",
            condition={"op": "range", "min": 0.0, "max": 100.0},
            weight=1.0,
        ),
        QualityRule(
            rule_id="power_range",
            name="Power Range",
            description="Power must be positive",
            dimension="validity",
            condition={"op": "range", "min": 0.0, "max": None},
            weight=1.0,
        ),
    ]

    def __init__(self, rules: Optional[list[QualityRule]] = None):
        self._rules = {r.rule_id: r for r in (rules or self.DEFAULT_RULES)}

    def add_rule(self, rule: QualityRule) -> None:
        """Add or update a quality rule."""
        self._rules[rule.rule_id] = rule

    def get_rules(self) -> list[QualityRule]:
        """Get all active rules."""
        return [r for r in self._rules.values() if r.enabled]

    def evaluate(self, property_code: str, value: float, metadata: dict) -> list[str]:
        """Evaluate all rules against a value. Returns list of triggered rule IDs."""
        triggered = []
        for rule in self.get_rules():
            passed, reason = rule.evaluate(value, metadata)
            if not passed:
                triggered.append(rule.rule_id)
                logger.debug("Rule '%s' triggered: %s", rule.rule_id, reason)
        return triggered

    def get_rules_by_dimension(self, dimension: str) -> list[QualityRule]:
        """Get rules for a specific dimension."""
        return [r for r in self._rules.values() if r.dimension == dimension and r.enabled]
