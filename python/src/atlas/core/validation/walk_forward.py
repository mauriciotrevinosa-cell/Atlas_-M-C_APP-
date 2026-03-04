"""
Walk-forward evaluation tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class WalkForwardResult:
    folds: list[dict[str, Any]]
    mean_test_return: float
    win_rate: float
    selected_strategies: list[str]
    n_folds: int


class WalkForwardAnalyzer:
    """Evaluates strategy stability with sequential train/test folds."""

    def analyze(
        self,
        strategy_returns: pd.DataFrame,
        train_size: int = 252,
        test_size: int = 63,
        step_size: int = 63,
    ) -> WalkForwardResult:
        if strategy_returns.empty or len(strategy_returns.columns) == 0:
            raise ValueError("strategy_returns cannot be empty")

        data = strategy_returns.apply(pd.to_numeric, errors="coerce").dropna(how="all")
        folds: list[dict[str, Any]] = []
        selected: list[str] = []
        all_test_returns: list[float] = []

        start = 0
        while start + train_size + test_size <= len(data):
            train = data.iloc[start : start + train_size]
            test = data.iloc[start + train_size : start + train_size + test_size]

            train_mu = train.mean(axis=0, skipna=True)
            chosen = str(train_mu.idxmax())
            selected.append(chosen)

            test_series = pd.to_numeric(test[chosen], errors="coerce").dropna()
            fold_ret = float(test_series.mean()) if not test_series.empty else 0.0
            all_test_returns.extend(test_series.tolist())

            folds.append(
                {
                    "start_row": int(start),
                    "train_rows": int(len(train)),
                    "test_rows": int(len(test)),
                    "selected_strategy": chosen,
                    "train_mean_return": float(train_mu.max()),
                    "test_mean_return": fold_ret,
                }
            )
            start += step_size

        if not folds:
            raise ValueError("No folds generated; adjust train/test sizes")

        arr = np.array(all_test_returns, dtype=float) if all_test_returns else np.array([0.0])
        return WalkForwardResult(
            folds=folds,
            mean_test_return=float(np.mean(arr)),
            win_rate=float(np.mean(arr > 0)),
            selected_strategies=selected,
            n_folds=len(folds),
        )

