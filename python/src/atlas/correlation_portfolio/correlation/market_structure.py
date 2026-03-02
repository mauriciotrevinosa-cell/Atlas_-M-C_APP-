"""
Market Structure & Correlation Analysis
========================================
Computes rolling and static correlation matrices, detects correlation regime
changes, and identifies market structure breakdowns.

Key Features:
  - Rolling correlation (DCC-like approximation)
  - Correlation regime detection (low/normal/high/crisis)
  - Average correlation trend (market structure health)
  - Correlation breakdown detection (sudden decoupling)
  - Network centrality (most/least connected assets)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.correlation.market_structure")


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CorrelationRegime:
    regime: str            # "low" | "normal" | "high" | "crisis"
    avg_correlation: float
    correlation_vol: float # Volatility of correlation itself
    percentile: float      # Where current corr sits in history (0-100)
    breakdown_detected: bool
    leading_assets: List[str]   # Most correlated (systemic risk)
    lagging_assets: List[str]   # Least correlated (diversifiers)


@dataclass
class MarketStructureReport:
    timestamp: pd.Timestamp
    tickers: List[str]
    corr_matrix: pd.DataFrame
    regime: CorrelationRegime
    rolling_avg_corr: pd.Series       # Time series of average correlation
    pairwise_changes: Dict[str, float] # Biggest correlation changes
    diversification_score: float      # 0=fully correlated, 1=fully diverse
    summary: Dict                     # Human-readable summary


# ─────────────────────────────────────────────────────────────────────────────
# Market Structure Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class MarketStructureAnalyzer:
    """
    Analyzes market correlation structure across assets.

    Usage
    -----
    analyzer = MarketStructureAnalyzer(window=60)
    report   = analyzer.analyze(price_df)
    """

    def __init__(
        self,
        window: int = 60,
        min_obs: int = 30,
        crisis_threshold: float = 0.70,
        high_threshold: float = 0.50,
        low_threshold: float = 0.20,
    ):
        self.window = window
        self.min_obs = min_obs
        self.crisis_threshold = crisis_threshold
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    # ── Core analysis ──────────────────────────────────────────────

    def analyze(self, prices: pd.DataFrame) -> MarketStructureReport:
        """
        Full market structure analysis.

        Parameters
        ----------
        prices : DataFrame with Date index and ticker columns (Close prices)
        """
        returns = prices.pct_change().dropna()
        if len(returns) < self.min_obs:
            raise ValueError(f"Need at least {self.min_obs} observations, got {len(returns)}")

        tickers   = list(returns.columns)
        timestamp = returns.index[-1]

        # Static full-period correlation matrix
        corr_matrix = returns.corr()

        # Rolling average correlation (market stress indicator)
        rolling_avg = self._rolling_avg_correlation(returns)

        # Current correlation regime
        regime = self._detect_regime(rolling_avg, corr_matrix)

        # Largest pairwise changes (last window vs prior window)
        pairwise_changes = self._pairwise_changes(returns)

        # Diversification score
        div_score = self._diversification_score(corr_matrix)

        return MarketStructureReport(
            timestamp=timestamp,
            tickers=tickers,
            corr_matrix=corr_matrix,
            regime=regime,
            rolling_avg_corr=rolling_avg,
            pairwise_changes=pairwise_changes,
            diversification_score=div_score,
            summary=self._build_summary(regime, div_score, tickers, corr_matrix),
        )

    def _rolling_avg_correlation(self, returns: pd.DataFrame) -> pd.Series:
        """Compute rolling average pairwise correlation."""
        tickers = list(returns.columns)
        n = len(tickers)
        if n < 2:
            return pd.Series(dtype=float)

        series_list = []
        for i in range(n):
            for j in range(i + 1, n):
                pair = returns[tickers[i]].rolling(self.window).corr(returns[tickers[j]])
                series_list.append(pair)

        if not series_list:
            return pd.Series(dtype=float)

        avg_corr = pd.concat(series_list, axis=1).mean(axis=1)
        return avg_corr.dropna()

    def _detect_regime(
        self, rolling_avg: pd.Series, corr_matrix: pd.DataFrame
    ) -> CorrelationRegime:
        """Classify current correlation regime."""
        if rolling_avg.empty:
            cur_avg = float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean())
            corr_vol = 0.0
            percentile = 50.0
        else:
            cur_avg   = float(rolling_avg.iloc[-1])
            corr_vol  = float(rolling_avg.std())
            historical = rolling_avg.dropna()
            percentile = float((historical < cur_avg).mean() * 100)

        # Classify regime
        if cur_avg >= self.crisis_threshold:
            regime_name = "crisis"
        elif cur_avg >= self.high_threshold:
            regime_name = "high"
        elif cur_avg <= self.low_threshold:
            regime_name = "low"
        else:
            regime_name = "normal"

        # Network centrality: sum of absolute correlations per asset
        tickers = list(corr_matrix.columns)
        centrality = {t: float(corr_matrix[t].abs().sum() - 1) / (len(tickers) - 1)
                      for t in tickers}
        sorted_c = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        leading  = [t for t, _ in sorted_c[:3]]
        lagging  = [t for t, _ in sorted_c[-3:]]

        # Breakdown: sudden spike in correlation vol
        breakdown = corr_vol > 0.15 and regime_name in ("high", "crisis")

        return CorrelationRegime(
            regime=regime_name,
            avg_correlation=round(cur_avg, 4),
            correlation_vol=round(corr_vol, 4),
            percentile=round(percentile, 1),
            breakdown_detected=breakdown,
            leading_assets=leading,
            lagging_assets=lagging,
        )

    def _pairwise_changes(self, returns: pd.DataFrame) -> Dict[str, float]:
        """Find pairs with largest recent vs historical correlation changes."""
        if len(returns) < self.window * 2:
            return {}

        tickers = list(returns.columns)
        recent  = returns.iloc[-self.window:].corr()
        prior   = returns.iloc[-self.window * 2:-self.window].corr()
        changes = {}
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                a, b = tickers[i], tickers[j]
                delta = float(recent.loc[a, b] - prior.loc[a, b])
                changes[f"{a}-{b}"] = round(delta, 4)

        return dict(sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True)[:10])

    def _diversification_score(self, corr_matrix: pd.DataFrame) -> float:
        """
        Diversification score: 1 - average absolute off-diagonal correlation.
        1.0 = perfectly uncorrelated (max diversification)
        0.0 = perfectly correlated (no diversification)
        """
        vals = corr_matrix.values
        mask = ~np.eye(len(vals), dtype=bool)
        avg_abs_corr = float(np.abs(vals[mask]).mean())
        return round(1 - avg_abs_corr, 4)

    def _build_summary(
        self, regime: CorrelationRegime, div_score: float,
        tickers: List[str], corr_matrix: pd.DataFrame
    ) -> Dict:
        return {
            "regime": regime.regime,
            "avg_correlation": regime.avg_correlation,
            "diversification_score": div_score,
            "breakdown_alert": regime.breakdown_detected,
            "n_assets": len(tickers),
            "systemic_risk_assets": regime.leading_assets,
            "diversifiers": regime.lagging_assets,
            "interpretation": self._interpret(regime, div_score),
        }

    @staticmethod
    def _interpret(regime: CorrelationRegime, div_score: float) -> str:
        msgs = {
            "crisis": "⚠ CRISIS: All assets moving together. Diversification ineffective. Reduce exposure.",
            "high":   "⚡ HIGH CORRELATION: Limited diversification benefit. Consider alternatives.",
            "normal": "✅ NORMAL: Healthy diversification potential. Portfolio construction advantaged.",
            "low":    "🟢 LOW CORRELATION: Maximum diversification benefit. Strong alpha opportunity.",
        }
        base = msgs.get(regime.regime, "Unknown regime")
        if regime.breakdown_detected:
            base += f" | BREAKDOWN detected in correlation structure."
        return base

    def top_correlated_pairs(
        self, corr_matrix: pd.DataFrame, n: int = 10, threshold: float = 0.6
    ) -> List[Tuple[str, str, float]]:
        """Return top N most correlated pairs above threshold."""
        tickers = list(corr_matrix.columns)
        pairs = []
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                c = float(corr_matrix.iloc[i, j])
                if abs(c) >= threshold:
                    pairs.append((tickers[i], tickers[j], round(c, 4)))
        return sorted(pairs, key=lambda x: abs(x[2]), reverse=True)[:n]
