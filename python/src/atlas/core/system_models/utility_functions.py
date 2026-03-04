"""
Strategy utility functions for probabilistic decision-making.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StrategyUtilityResult:
    utility: float
    expected_return: float
    risk_penalty: float
    cost_penalty: float
    uncertainty_penalty: float
    details: dict[str, Any] = field(default_factory=dict)


class StrategyUtility:
    """Computes utility score balancing return, risk, friction, and uncertainty."""

    def __init__(
        self,
        risk_aversion: float = 1.5,
        cost_weight: float = 1.0,
        uncertainty_weight: float = 1.0,
    ) -> None:
        self.risk_aversion = float(risk_aversion)
        self.cost_weight = float(cost_weight)
        self.uncertainty_weight = float(uncertainty_weight)

    def evaluate(
        self,
        expected_return: float,
        risk: float,
        cost: float,
        uncertainty: float,
        leverage: float = 1.0,
    ) -> StrategyUtilityResult:
        exp_ret = float(expected_return) * float(leverage)
        risk_penalty = self.risk_aversion * (float(risk) ** 2)
        cost_penalty = self.cost_weight * abs(float(cost))
        uncertainty_penalty = self.uncertainty_weight * abs(float(uncertainty))
        utility = exp_ret - risk_penalty - cost_penalty - uncertainty_penalty

        return StrategyUtilityResult(
            utility=float(utility),
            expected_return=float(exp_ret),
            risk_penalty=float(risk_penalty),
            cost_penalty=float(cost_penalty),
            uncertainty_penalty=float(uncertainty_penalty),
            details={
                "risk_aversion": self.risk_aversion,
                "cost_weight": self.cost_weight,
                "uncertainty_weight": self.uncertainty_weight,
                "leverage": float(leverage),
            },
        )

