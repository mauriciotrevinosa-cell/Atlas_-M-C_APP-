"""
Probability of Backtest Overfitting (PBO) analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log

import numpy as np
import pandas as pd


@dataclass(slots=True)
class PBOResult:
    pbo: float
    lambdas: list[float]
    rank_percentiles: list[float]
    selected_strategies: list[str]
    n_trials: int


class PBOAnalyzer:
    """
    Computes a practical PBO estimate using rolling train/test folds.
    """

    def analyze(self, strategy_returns: pd.DataFrame, n_splits: int = 8) -> PBOResult:
        if strategy_returns.empty or len(strategy_returns.columns) < 2:
            raise ValueError("PBOAnalyzer requires at least 2 strategy columns")

        clean = strategy_returns.apply(pd.to_numeric, errors="coerce").dropna(how="all")
        n_rows = len(clean)
        if n_rows < n_splits * 2:
            raise ValueError("Not enough rows for requested n_splits")

        fold_size = n_rows // n_splits
        if fold_size < 2:
            raise ValueError("Fold size is too small")

        lambdas: list[float] = []
        ranks: list[float] = []
        selected: list[str] = []

        for split in range(n_splits):
            test_start = split * fold_size
            test_end = (split + 1) * fold_size if split < n_splits - 1 else n_rows
            test_idx = clean.index[test_start:test_end]
            train_idx = clean.index.difference(test_idx)

            train = clean.loc[train_idx]
            test = clean.loc[test_idx]
            if train.empty or test.empty:
                continue

            train_mu = train.mean(axis=0, skipna=True)
            best_strategy = str(train_mu.idxmax())
            selected.append(best_strategy)

            test_mu = test.mean(axis=0, skipna=True).sort_values(ascending=False)
            if best_strategy not in test_mu.index:
                continue

            rank = int(test_mu.index.get_loc(best_strategy)) + 1
            n = len(test_mu)
            percentile = (rank - 0.5) / max(n, 1)
            percentile = float(min(max(percentile, 1e-6), 1.0 - 1e-6))
            lam = log(percentile / (1.0 - percentile))

            ranks.append(percentile)
            lambdas.append(float(lam))

        n_trials = len(lambdas)
        if n_trials == 0:
            raise ValueError("Unable to compute PBO: no valid folds")

        pbo = float(np.mean(np.array(lambdas) <= 0.0))
        return PBOResult(
            pbo=pbo,
            lambdas=lambdas,
            rank_percentiles=ranks,
            selected_strategies=selected,
            n_trials=n_trials,
        )
