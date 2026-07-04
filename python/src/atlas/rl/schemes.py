"""
Action and reward schemes for Atlas RL trading environments.

The goal is to make the environment contract explicit without adding a heavy
RL framework dependency. These small scheme objects are serializable, testable,
and reusable by trainers, APIs, or future MMO simulation layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Iterable, List, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class TradeAction:
    """One discrete action available to a trading policy."""

    action_id: int
    name: str
    side: str
    size_pct: float = 0.0
    label: str = ""

    def __post_init__(self) -> None:
        side = self.side.lower()
        if side not in {"hold", "buy", "sell"}:
            raise ValueError(f"Unsupported trade action side: {self.side}")
        if self.action_id < 0:
            raise ValueError("action_id must be non-negative")
        if self.size_pct < 0:
            raise ValueError("size_pct must be non-negative")
        object.__setattr__(self, "side", side)
        if not self.label:
            object.__setattr__(self, "label", self.name)

    def to_dict(self) -> Dict[str, object]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "side": self.side,
            "size_pct": self.size_pct,
            "label": self.label,
        }


class ActionScheme:
    """Validated discrete action contract for an RL environment."""

    def __init__(self, actions: Sequence[TradeAction]):
        if not actions:
            raise ValueError("ActionScheme requires at least one action")

        by_id: Dict[int, TradeAction] = {}
        for action in actions:
            if action.action_id in by_id:
                raise ValueError(f"Duplicate action_id: {action.action_id}")
            by_id[action.action_id] = action

        missing = sorted(set(range(max(by_id) + 1)) - set(by_id))
        if missing:
            raise ValueError(f"Action ids must be contiguous; missing {missing}")

        self._actions = dict(sorted(by_id.items()))

    @classmethod
    def single_asset_default(cls) -> "ActionScheme":
        return cls(
            [
                TradeAction(0, "HOLD", "hold", 0.0, "HOLD"),
                TradeAction(1, "BUY_SMALL", "buy", 0.10, "BUY_SM"),
                TradeAction(2, "BUY_LARGE", "buy", 0.25, "BUY_LG"),
                TradeAction(3, "SELL_SMALL", "sell", 0.10, "SELL_SM"),
                TradeAction(4, "SELL_LARGE", "sell", 0.25, "SELL_LG"),
            ]
        )

    @property
    def actions(self) -> Mapping[int, TradeAction]:
        return self._actions

    @property
    def action_dim(self) -> int:
        return len(self._actions)

    def validate(self, action: int) -> TradeAction:
        try:
            return self._actions[int(action)]
        except (KeyError, TypeError, ValueError) as exc:
            valid = ", ".join(str(key) for key in self._actions)
            raise ValueError(f"Invalid action {action}; expected one of {valid}") from exc

    def names(self) -> List[str]:
        return [action.name for action in self._actions.values()]

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": "discrete_single_asset",
            "action_dim": self.action_dim,
            "actions": [action.to_dict() for action in self._actions.values()],
        }


@dataclass(frozen=True)
class RewardBreakdown:
    """Reward value plus explainable components."""

    total: float
    base_return: float
    sharpe_bonus: float
    drawdown_penalty: float
    turnover_penalty: float
    cost_penalty: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "total": float(self.total),
            "base_return": float(self.base_return),
            "sharpe_bonus": float(self.sharpe_bonus),
            "drawdown_penalty": float(self.drawdown_penalty),
            "turnover_penalty": float(self.turnover_penalty),
            "cost_penalty": float(self.cost_penalty),
        }


@dataclass(frozen=True)
class RiskAdjustedRewardScheme:
    """
    Sharpe-shaped PnL reward with configurable risk and friction penalties.

    Defaults match the legacy TradingEnvironment behavior: base step return,
    a small Sharpe bonus after enough observations, and a drawdown penalty when
    drawdown breaches -5%.
    """

    sharpe_window: int = 20
    min_sharpe_samples: int = 10
    sharpe_weight: float = 0.001
    drawdown_threshold: float = -0.05
    drawdown_weight: float = 0.5
    turnover_weight: float = 0.0
    cost_weight: float = 0.0

    def compute(
        self,
        step_return: float,
        recent_returns: Iterable[float],
        *,
        drawdown: float,
        turnover: float = 0.0,
        trade_cost: float = 0.0,
    ) -> RewardBreakdown:
        base = float(step_return)
        sharpe_bonus = 0.0
        values = list(recent_returns)

        if len(values) > self.min_sharpe_samples and self.sharpe_weight:
            arr = np.asarray(values[-self.sharpe_window :], dtype=np.float64)
            sharpe = float(arr.mean() / (arr.std() + 1e-9) * sqrt(252))
            sharpe_bonus = self.sharpe_weight * sharpe

        drawdown_penalty = 0.0
        if drawdown < self.drawdown_threshold:
            drawdown_penalty = self.drawdown_weight * float(drawdown)

        turnover_penalty = -abs(float(turnover)) * self.turnover_weight
        cost_penalty = -abs(float(trade_cost)) * self.cost_weight

        total = base + sharpe_bonus + drawdown_penalty + turnover_penalty + cost_penalty
        return RewardBreakdown(
            total=float(total),
            base_return=base,
            sharpe_bonus=float(sharpe_bonus),
            drawdown_penalty=float(drawdown_penalty),
            turnover_penalty=float(turnover_penalty),
            cost_penalty=float(cost_penalty),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": "risk_adjusted",
            "sharpe_window": self.sharpe_window,
            "min_sharpe_samples": self.min_sharpe_samples,
            "sharpe_weight": self.sharpe_weight,
            "drawdown_threshold": self.drawdown_threshold,
            "drawdown_weight": self.drawdown_weight,
            "turnover_weight": self.turnover_weight,
            "cost_weight": self.cost_weight,
        }
