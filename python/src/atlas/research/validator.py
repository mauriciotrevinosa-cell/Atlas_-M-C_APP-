"""
Statistical validation utilities for research hypotheses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from atlas.core.validation.bootstrap_tests import BootstrapTests


@dataclass(slots=True)
class ValidationResult:
    p_value: float
    effect_size: float
    ci_low: float
    ci_high: float
    significant: bool


class StatisticalValidator:
    """Evaluates whether observed strategy returns are statistically meaningful."""

    def __init__(self) -> None:
        self.bootstrap = BootstrapTests()

    def validate(
        self,
        returns: pd.Series,
        alpha: float = 0.05,
        n_bootstrap: int = 2000,
    ) -> ValidationResult:
        clean = pd.to_numeric(returns, errors="coerce").dropna()
        if clean.empty:
            return ValidationResult(
                p_value=1.0,
                effect_size=0.0,
                ci_low=0.0,
                ci_high=0.0,
                significant=False,
            )

        boot = self.bootstrap.mean_return_test(
            clean,
            n_bootstrap=n_bootstrap,
            alpha=alpha,
        )
        std = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
        effect = float(clean.mean() / std) if std > 0 else 0.0

        return ValidationResult(
            p_value=float(boot.p_value),
            effect_size=float(effect),
            ci_low=float(boot.ci_low),
            ci_high=float(boot.ci_high),
            significant=bool(boot.significant),
        )

