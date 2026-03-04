"""
Composite strategy quality scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bootstrap_tests import BootstrapResult
from .pbo import PBOResult
from .walk_forward import WalkForwardResult


@dataclass(slots=True)
class StrategyScore:
    score: float
    rating: str
    components: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyScorer:
    """Combines overfitting risk, walk-forward performance, and significance."""

    def score(
        self,
        pbo: PBOResult,
        walk_forward: WalkForwardResult,
        bootstrap: BootstrapResult,
    ) -> StrategyScore:
        pbo_component = max(0.0, 1.0 - pbo.pbo) * 40.0
        wf_component = max(0.0, walk_forward.win_rate) * 30.0
        mean_component = max(0.0, min(1.0, walk_forward.mean_test_return * 100.0 + 0.5)) * 20.0
        sig_component = (1.0 if bootstrap.significant else max(0.0, 1.0 - bootstrap.p_value)) * 10.0

        total = pbo_component + wf_component + mean_component + sig_component
        rating = _rating(total)

        return StrategyScore(
            score=float(total),
            rating=rating,
            components={
                "pbo_component": float(pbo_component),
                "walk_forward_component": float(wf_component),
                "mean_return_component": float(mean_component),
                "significance_component": float(sig_component),
            },
            metadata={
                "pbo": pbo.pbo,
                "win_rate": walk_forward.win_rate,
                "mean_test_return": walk_forward.mean_test_return,
                "bootstrap_p_value": bootstrap.p_value,
            },
        )


def _rating(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"

