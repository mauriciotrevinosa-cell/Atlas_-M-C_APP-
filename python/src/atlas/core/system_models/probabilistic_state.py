"""
Probabilistic market state model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(slots=True)
class MarketState:
    name: str
    probability: float
    expected_return: float
    expected_volatility: float


@dataclass(slots=True)
class StateDistribution:
    states: list[MarketState]
    entropy: float
    most_likely_state: str
    transition_hint: str


class ProbabilisticStateModel:
    """
    Infers market regime probabilities from a compact feature set.
    """

    def infer(self, features: Mapping[str, float]) -> StateDistribution:
        f = {k: float(v) for k, v in features.items()}
        momentum = f.get("momentum", 0.0)
        volatility = abs(f.get("volatility", 0.2))
        liquidity = f.get("liquidity", 0.0)
        stress = max(0.0, f.get("stress", 0.0))

        score_bull = 1.2 * momentum - 0.6 * volatility + 0.2 * liquidity
        score_bear = -1.3 * momentum + 0.8 * volatility + 0.4 * stress
        score_range = -abs(momentum) + 0.4 * liquidity - 0.2 * stress
        score_shock = 1.2 * stress + 1.0 * volatility - 0.5 * liquidity

        labels = ["bull", "bear", "range", "shock"]
        scores = np.array([score_bull, score_bear, score_range, score_shock], dtype=float)
        probs = _softmax(scores)

        expectations = {
            "bull": (0.12, 0.18),
            "bear": (-0.15, 0.30),
            "range": (0.02, 0.12),
            "shock": (-0.25, 0.45),
        }

        states = [
            MarketState(
                name=label,
                probability=float(prob),
                expected_return=float(expectations[label][0]),
                expected_volatility=float(expectations[label][1]),
            )
            for label, prob in zip(labels, probs)
        ]
        states.sort(key=lambda s: s.probability, reverse=True)

        entropy = float(-np.sum(probs * np.log(np.maximum(probs, 1e-12))))
        top = states[0].name if states else "range"
        hint = self._transition_hint(top, stress=stress, momentum=momentum)

        return StateDistribution(
            states=states,
            entropy=entropy,
            most_likely_state=top,
            transition_hint=hint,
        )

    def _transition_hint(self, state: str, stress: float, momentum: float) -> str:
        if state == "shock" and stress > 0.8:
            return "Risk-off until volatility compresses."
        if state == "bull" and momentum > 0.5:
            return "Trend continuation likely if liquidity stays stable."
        if state == "bear" and stress > 0.5:
            return "Defensive posture favored; monitor rebound signals."
        return "Range/transition regime: prioritize mean-reversion filters."


def _softmax(x: np.ndarray) -> np.ndarray:
    z = x - np.max(x)
    ex = np.exp(z)
    return ex / np.sum(ex)

