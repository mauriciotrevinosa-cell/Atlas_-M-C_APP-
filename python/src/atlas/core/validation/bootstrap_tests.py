"""
Bootstrap significance tests for strategy returns.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class BootstrapResult:
    p_value: float
    ci_low: float
    ci_high: float
    observed_stat: float
    null_mean: float
    significant: bool


class BootstrapTests:
    """Bootstrap and permutation-inspired tests for return statistics."""

    def mean_return_test(
        self,
        returns: pd.Series,
        n_bootstrap: int = 2000,
        alpha: float = 0.05,
        seed: int = 42,
    ) -> BootstrapResult:
        clean = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(dtype=float)
        if clean.size < 10:
            raise ValueError("Need at least 10 samples for bootstrap test")

        rng = np.random.default_rng(seed)
        observed = float(np.mean(clean))
        samples = rng.choice(clean, size=(n_bootstrap, clean.size), replace=True)
        means = samples.mean(axis=1)

        ci_low = float(np.quantile(means, alpha / 2))
        ci_high = float(np.quantile(means, 1.0 - alpha / 2))

        centered = clean - np.mean(clean)
        null_samples = rng.choice(centered, size=(n_bootstrap, centered.size), replace=True)
        null_means = null_samples.mean(axis=1)
        p_value = float(np.mean(np.abs(null_means) >= abs(observed)))

        return BootstrapResult(
            p_value=p_value,
            ci_low=ci_low,
            ci_high=ci_high,
            observed_stat=observed,
            null_mean=float(np.mean(null_means)),
            significant=bool(p_value < alpha and (ci_low > 0 or ci_high < 0)),
        )

    def sharpe_ratio_test(
        self,
        returns: pd.Series,
        n_bootstrap: int = 2000,
        alpha: float = 0.05,
        seed: int = 42,
    ) -> BootstrapResult:
        clean = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(dtype=float)
        if clean.size < 10:
            raise ValueError("Need at least 10 samples for bootstrap test")

        rng = np.random.default_rng(seed)
        observed = _sharpe(clean)
        boot = np.array([_sharpe(rng.choice(clean, size=clean.size, replace=True)) for _ in range(n_bootstrap)])
        ci_low = float(np.quantile(boot, alpha / 2))
        ci_high = float(np.quantile(boot, 1.0 - alpha / 2))
        p_value = float(np.mean(boot <= 0.0))

        return BootstrapResult(
            p_value=p_value,
            ci_low=ci_low,
            ci_high=ci_high,
            observed_stat=float(observed),
            null_mean=0.0,
            significant=bool(p_value < alpha and ci_low > 0.0),
        )


def _sharpe(values: np.ndarray) -> float:
    std = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
    if std <= 0:
        return 0.0
    return float(np.mean(values) / std * np.sqrt(252.0))

