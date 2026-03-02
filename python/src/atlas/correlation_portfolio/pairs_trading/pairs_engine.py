"""
Pairs Trading Engine — Statistical Arbitrage
==============================================
Implements cointegration-based pairs trading:

1. Pair Selection:   Engle-Granger cointegration test (simplified ADF)
2. Spread Modeling:  OLS hedge ratio + spread calculation
3. Signal Generation: Z-score of spread → entry/exit thresholds
4. Position Sizing:  Dollar-neutral long/short

Strategy:
  Entry BUY spread:  Z-score < -entry_z  (spread too low → revert up)
  Entry SELL spread: Z-score > +entry_z  (spread too high → revert down)
  Exit:              |Z-score| < exit_z  (mean reversion achieved)
  Stop:              |Z-score| > stop_z  (cointegration breakdown)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.pairs_trading")


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PairStats:
    ticker_a: str
    ticker_b: str
    hedge_ratio: float        # β: position in B per unit of A
    half_life: float          # Mean reversion half-life (days)
    correlation: float
    adf_pvalue: float         # ADF test p-value (lower = more cointegrated)
    is_cointegrated: bool     # True if p < 0.05
    spread_mean: float
    spread_std: float
    current_zscore: float


@dataclass
class PairSignal:
    ticker_a: str
    ticker_b: str
    action: str               # "LONG_SPREAD" | "SHORT_SPREAD" | "EXIT" | "STOP"
    zscore: float
    confidence: float
    hedge_ratio: float
    reasoning: str


# ─────────────────────────────────────────────────────────────────────────────
# Pairs Engine
# ─────────────────────────────────────────────────────────────────────────────

class PairsEngine:
    """
    Identifies cointegrated pairs and generates spread trading signals.

    Usage
    -----
    engine = PairsEngine()
    pairs  = engine.find_pairs(prices_df)             # screen universe
    stats  = engine.compute_pair_stats(prices, 'A', 'B')
    signal = engine.get_signal(stats, prices)
    """

    def __init__(
        self,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_z: float = 3.5,
        lookback: int = 252,
        min_half_life: float = 2.0,
        max_half_life: float = 60.0,
        min_correlation: float = 0.60,
        max_adf_pvalue: float = 0.10,
    ):
        self.entry_z         = entry_z
        self.exit_z          = exit_z
        self.stop_z          = stop_z
        self.lookback        = lookback
        self.min_half_life   = min_half_life
        self.max_half_life   = max_half_life
        self.min_correlation = min_correlation
        self.max_adf_pvalue  = max_adf_pvalue

    # ── Statistical Methods ────────────────────────────────────────

    @staticmethod
    def _adf_pvalue(series: np.ndarray) -> float:
        """
        Simplified ADF test using OLS regression.
        Tests H0: unit root (non-stationary).
        p-value approximated from ADF statistic via lookup table.
        """
        y    = series[1:]
        y_l  = series[:-1]
        dy   = y - y_l
        # OLS: Δy = α + β·y_{t-1}
        X = np.column_stack([np.ones(len(y_l)), y_l])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, dy, rcond=None)
            beta = coeffs[1]
            residuals = dy - X @ coeffs
            se = np.sqrt(np.var(residuals) / (np.var(y_l) * len(y_l)))
            adf_stat = beta / (se + 1e-10)
        except Exception:
            return 0.99

        # MacKinnon (1994) critical values approximation:
        # p < 0.01: stat < -3.43 | p < 0.05: stat < -2.86 | p < 0.10: stat < -2.57
        if adf_stat < -3.43:  return 0.01
        if adf_stat < -2.86:  return 0.05
        if adf_stat < -2.57:  return 0.10
        if adf_stat < -1.94:  return 0.25
        return 0.50

    @staticmethod
    def _half_life(spread: np.ndarray) -> float:
        """
        Estimate mean-reversion half-life via OLS on the spread process:
        Δspread_t = α + β·spread_{t-1}
        Half-life = -ln(2) / β
        """
        y  = spread[1:]
        yl = spread[:-1]
        dy = y - yl
        X  = np.column_stack([np.ones(len(yl)), yl])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, dy, rcond=None)
            beta = coeffs[1]
            if beta >= 0:
                return np.inf
            return -np.log(2) / beta
        except Exception:
            return np.inf

    @staticmethod
    def _ols_hedge_ratio(y: np.ndarray, x: np.ndarray) -> float:
        """OLS regression of y on x to get hedge ratio."""
        X = np.column_stack([np.ones(len(x)), x])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            return float(coeffs[1])
        except Exception:
            return 1.0

    # ── Pair Analysis ─────────────────────────────────────────────

    def compute_pair_stats(
        self, prices: pd.DataFrame, ticker_a: str, ticker_b: str
    ) -> PairStats:
        """
        Compute full statistical profile for a single pair.
        """
        df = prices[[ticker_a, ticker_b]].dropna().iloc[-self.lookback:]
        if len(df) < 60:
            return PairStats(
                ticker_a=ticker_a, ticker_b=ticker_b,
                hedge_ratio=1.0, half_life=999.0, correlation=0.0,
                adf_pvalue=0.99, is_cointegrated=False,
                spread_mean=0.0, spread_std=1.0, current_zscore=0.0,
            )

        a = df[ticker_a].values
        b = df[ticker_b].values

        corr         = float(np.corrcoef(a, b)[0, 1])
        hedge_ratio  = self._ols_hedge_ratio(a, b)
        spread       = a - hedge_ratio * b
        adf_p        = self._adf_pvalue(spread)
        hl           = self._half_life(spread)

        spread_mean  = float(np.mean(spread))
        spread_std   = float(np.std(spread)) or 1.0
        cur_zscore   = float((spread[-1] - spread_mean) / spread_std)

        return PairStats(
            ticker_a=ticker_a,
            ticker_b=ticker_b,
            hedge_ratio=round(hedge_ratio, 4),
            half_life=round(hl, 2),
            correlation=round(corr, 4),
            adf_pvalue=round(adf_p, 4),
            is_cointegrated=(adf_p <= self.max_adf_pvalue),
            spread_mean=round(spread_mean, 6),
            spread_std=round(spread_std, 6),
            current_zscore=round(cur_zscore, 4),
        )

    def find_pairs(
        self, prices: pd.DataFrame, max_pairs: int = 20
    ) -> List[PairStats]:
        """
        Screen all ticker combinations and return best cointegrated pairs.
        """
        tickers = list(prices.columns)
        candidates: List[PairStats] = []

        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                a, b = tickers[i], tickers[j]
                try:
                    stats = self.compute_pair_stats(prices, a, b)
                    if (stats.is_cointegrated
                            and stats.correlation >= self.min_correlation
                            and self.min_half_life <= stats.half_life <= self.max_half_life):
                        candidates.append(stats)
                except Exception as e:
                    logger.debug("Pair %s-%s failed: %s", a, b, e)

        # Rank by ADF p-value (lower = better cointegration)
        candidates.sort(key=lambda s: s.adf_pvalue)
        logger.info("Found %d cointegrated pairs (showing top %d)", len(candidates), max_pairs)
        return candidates[:max_pairs]

    # ── Signal Generation ─────────────────────────────────────────

    def get_signal(self, stats: PairStats, prices: pd.DataFrame) -> Optional[PairSignal]:
        """
        Generate a trading signal based on current z-score.
        """
        if not stats.is_cointegrated:
            return None

        z = stats.current_zscore

        if abs(z) > self.stop_z:
            return PairSignal(
                ticker_a=stats.ticker_a, ticker_b=stats.ticker_b,
                action="STOP", zscore=z,
                confidence=0.9, hedge_ratio=stats.hedge_ratio,
                reasoning=f"Z={z:.2f} > stop={self.stop_z:.1f}: cointegration breakdown, exit immediately",
            )

        if z < -self.entry_z:
            conf = min(0.92, 0.55 + (abs(z) - self.entry_z) / (self.stop_z - self.entry_z) * 0.35)
            return PairSignal(
                ticker_a=stats.ticker_a, ticker_b=stats.ticker_b,
                action="LONG_SPREAD", zscore=z,
                confidence=conf, hedge_ratio=stats.hedge_ratio,
                reasoning=(
                    f"BUY {stats.ticker_a} / SELL {stats.ticker_b:.0f}×{stats.hedge_ratio:.2f} "
                    f"| Z={z:.2f} < -{self.entry_z:.1f} | HL={stats.half_life:.1f}d"
                ),
            )

        if z > self.entry_z:
            conf = min(0.92, 0.55 + (z - self.entry_z) / (self.stop_z - self.entry_z) * 0.35)
            return PairSignal(
                ticker_a=stats.ticker_a, ticker_b=stats.ticker_b,
                action="SHORT_SPREAD", zscore=z,
                confidence=conf, hedge_ratio=stats.hedge_ratio,
                reasoning=(
                    f"SELL {stats.ticker_a} / BUY {stats.ticker_b:.0f}×{stats.hedge_ratio:.2f} "
                    f"| Z={z:.2f} > +{self.entry_z:.1f} | HL={stats.half_life:.1f}d"
                ),
            )

        if abs(z) < self.exit_z:
            return PairSignal(
                ticker_a=stats.ticker_a, ticker_b=stats.ticker_b,
                action="EXIT", zscore=z,
                confidence=0.85, hedge_ratio=stats.hedge_ratio,
                reasoning=f"Z={z:.2f} within exit zone ±{self.exit_z:.1f}: mean reversion achieved",
            )

        return None  # In between — hold current position

    def get_all_signals(
        self, prices: pd.DataFrame, pairs: Optional[List[PairStats]] = None
    ) -> List[PairSignal]:
        """Run get_signal on a pre-computed list of pairs."""
        if pairs is None:
            pairs = self.find_pairs(prices)
        signals = []
        for p in pairs:
            sig = self.get_signal(p, prices)
            if sig:
                signals.append(sig)
        return signals
