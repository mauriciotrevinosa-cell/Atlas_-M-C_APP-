"""
Purged time-series cross-validation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

import numpy as np
import pandas as pd


@dataclass(slots=True)
class CVFold:
    train_idx: np.ndarray
    test_idx: np.ndarray
    purged_count: int


class PurgedCrossValidator:
    """Generates purged and embargoed folds for time-ordered samples."""

    def __init__(self, n_splits: int = 5, purge: int = 0, embargo_pct: float = 0.01) -> None:
        self.n_splits = max(2, int(n_splits))
        self.purge = max(0, int(purge))
        self.embargo_pct = max(0.0, float(embargo_pct))

    def split(self, index: Iterable) -> Iterator[CVFold]:
        idx = np.arange(len(list(index)))
        n = len(idx)
        if n < self.n_splits:
            raise ValueError("Not enough samples for n_splits")

        fold_sizes = np.full(self.n_splits, n // self.n_splits, dtype=int)
        fold_sizes[: n % self.n_splits] += 1

        current = 0
        embargo = int(np.ceil(n * self.embargo_pct))
        for fold_size in fold_sizes:
            start, stop = current, current + fold_size
            test_idx = idx[start:stop]

            purge_start = max(0, start - self.purge)
            purge_stop = min(n, stop + self.purge)
            embargo_stop = min(n, stop + embargo)

            train_mask = np.ones(n, dtype=bool)
            train_mask[purge_start:purge_stop] = False
            train_mask[stop:embargo_stop] = False
            train_idx = idx[train_mask]

            purged_count = int(n - train_mask.sum() - len(test_idx))
            yield CVFold(train_idx=train_idx, test_idx=test_idx, purged_count=max(0, purged_count))
            current = stop

    def split_frame(self, frame: pd.DataFrame) -> Iterator[CVFold]:
        return self.split(frame.index)

