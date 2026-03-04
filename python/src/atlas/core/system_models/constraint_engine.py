"""
Constraint engine for risk and execution feasibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class ConstraintSet:
    max_leverage: float = 2.0
    max_turnover: float = 0.5
    min_liquidity: float = 1_000_000.0
    max_volatility: float = 0.6
    max_position_concentration: float = 0.35


@dataclass(slots=True)
class ConstraintViolation:
    name: str
    value: float
    limit: float
    message: str
    severity: str = "error"


class ConstraintEngine:
    """Evaluates metrics against a configurable set of portfolio constraints."""

    def __init__(self, default_constraints: ConstraintSet | None = None) -> None:
        self.default_constraints = default_constraints or ConstraintSet()

    def evaluate(
        self,
        metrics: Mapping[str, float],
        constraints: ConstraintSet | None = None,
    ) -> list[ConstraintViolation]:
        c = constraints or self.default_constraints
        m = {k: float(v) for k, v in metrics.items()}
        violations: list[ConstraintViolation] = []

        leverage = m.get("leverage")
        if leverage is not None and leverage > c.max_leverage:
            violations.append(
                ConstraintViolation(
                    name="max_leverage",
                    value=leverage,
                    limit=c.max_leverage,
                    message=f"Leverage {leverage:.2f} exceeds limit {c.max_leverage:.2f}",
                )
            )

        turnover = m.get("turnover")
        if turnover is not None and turnover > c.max_turnover:
            violations.append(
                ConstraintViolation(
                    name="max_turnover",
                    value=turnover,
                    limit=c.max_turnover,
                    message=f"Turnover {turnover:.2f} exceeds limit {c.max_turnover:.2f}",
                )
            )

        liquidity = m.get("liquidity")
        if liquidity is not None and liquidity < c.min_liquidity:
            violations.append(
                ConstraintViolation(
                    name="min_liquidity",
                    value=liquidity,
                    limit=c.min_liquidity,
                    message=f"Liquidity {liquidity:.0f} below minimum {c.min_liquidity:.0f}",
                )
            )

        volatility = m.get("volatility")
        if volatility is not None and volatility > c.max_volatility:
            violations.append(
                ConstraintViolation(
                    name="max_volatility",
                    value=volatility,
                    limit=c.max_volatility,
                    message=f"Volatility {volatility:.2f} exceeds limit {c.max_volatility:.2f}",
                )
            )

        concentration = m.get("position_concentration")
        if concentration is not None and concentration > c.max_position_concentration:
            violations.append(
                ConstraintViolation(
                    name="max_position_concentration",
                    value=concentration,
                    limit=c.max_position_concentration,
                    message=f"Concentration {concentration:.2f} exceeds limit {c.max_position_concentration:.2f}",
                )
            )

        return violations

    def is_feasible(
        self,
        metrics: Mapping[str, float],
        constraints: ConstraintSet | None = None,
    ) -> bool:
        return len(self.evaluate(metrics=metrics, constraints=constraints)) == 0

