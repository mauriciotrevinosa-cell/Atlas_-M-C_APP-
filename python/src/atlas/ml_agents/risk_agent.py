"""
Risk Agent — Swarm Committee Member
=====================================
Specialized agent focused on portfolio risk, drawdown, VaR, and tail-risk metrics.
Feeds risk assessment to the SwarmCoordinator (ARIA).

Metrics produced:
  - Value at Risk (VaR 95%, 99%)
  - Conditional VaR (CVaR / Expected Shortfall)
  - Maximum Drawdown
  - Volatility regime classification
  - Correlation risk with broader market
  - Stress test result (historical shock scenarios)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.ml_agents.risk_agent")


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class RiskReport:
    """Structured output from the Risk Agent."""
    symbol: str
    var_95: float = 0.0          # Value at Risk 95% (as negative %)
    var_99: float = 0.0          # Value at Risk 99%
    cvar_95: float = 0.0         # Conditional VaR (Expected Shortfall)
    max_drawdown: float = 0.0    # Max historical drawdown (negative)
    volatility: float = 0.0      # Annualised volatility
    vol_regime: str = "UNKNOWN"  # LOW / MEDIUM / HIGH / CRISIS
    stress_loss: float = 0.0     # Worst stress scenario loss
    market_beta: float = 1.0     # Beta vs SPY proxy
    risk_score: float = 0.5      # 0 = extreme risk, 1 = very safe
    verdict: str = "HOLD"        # BUY / HOLD / REDUCE / EXIT
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "var_95": round(self.var_95, 4),
            "var_99": round(self.var_99, 4),
            "cvar_95": round(self.cvar_95, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "volatility": round(self.volatility, 4),
            "vol_regime": self.vol_regime,
            "stress_loss": round(self.stress_loss, 4),
            "market_beta": round(self.market_beta, 3),
            "risk_score": round(self.risk_score, 3),
            "verdict": self.verdict,
            "reasoning": self.reasoning,
        }


# ── Historical Shock Scenarios ────────────────────────────────────────────────

STRESS_SCENARIOS: List[Dict[str, float]] = [
    {"name": "COVID Crash (Mar 2020)",   "market_drop": -0.34, "vol_spike": 3.5},
    {"name": "GFC Peak (Oct 2008)",      "market_drop": -0.55, "vol_spike": 5.0},
    {"name": "Dot-com Peak (Mar 2000)",  "market_drop": -0.49, "vol_spike": 2.5},
    {"name": "Flash Crash (May 2010)",   "market_drop": -0.09, "vol_spike": 2.0},
    {"name": "Rate Shock (2022)",        "market_drop": -0.25, "vol_spike": 2.0},
    {"name": "Black Monday (Oct 1987)",  "market_drop": -0.23, "vol_spike": 6.0},
]


# ══════════════════════════════════════════════════════════════════════════════
#  RiskAgent
# ══════════════════════════════════════════════════════════════════════════════

class RiskAgent:
    """
    Swarm committee member: Risk Specialist.

    Analyses historical OHLCV data and computes comprehensive risk metrics.
    Output is a RiskReport that feeds into the SwarmCoordinator.

    Usage:
        agent = RiskAgent()
        report = agent.analyse("AAPL", ohlcv_df, market_df=spy_df)
        print(report.to_dict())
    """

    # ── Volatility regime thresholds (annualised) ─────────────────────────
    VOL_THRESHOLDS = {
        "LOW":    0.15,
        "MEDIUM": 0.25,
        "HIGH":   0.40,
    }

    def __init__(
        self,
        var_window: int = 252,
        risk_free_rate: float = 0.045,
    ):
        self.var_window      = var_window
        self.risk_free_rate  = risk_free_rate
        logger.info("RiskAgent initialised (window=%d, rf=%.1f%%)", var_window, risk_free_rate * 100)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        market_df: Optional[pd.DataFrame] = None,
    ) -> RiskReport:
        """
        Main analysis entry-point.

        Parameters
        ----------
        symbol    : Ticker symbol
        ohlcv     : DataFrame with Open/High/Low/Close/Volume (case-insensitive cols)
        market_df : Optional SPY/index OHLCV for beta calculation

        Returns RiskReport instance.
        """
        report = RiskReport(symbol=symbol)

        if ohlcv is None or len(ohlcv) < 20:
            report.reasoning.append("Insufficient data (<20 bars) — all metrics defaulted")
            report.verdict = "HOLD"
            return report

        try:
            closes = self._get_closes(ohlcv)
            returns = closes.pct_change().dropna()

            report.var_95        = self._var(returns, 0.95)
            report.var_99        = self._var(returns, 0.99)
            report.cvar_95       = self._cvar(returns, 0.95)
            report.max_drawdown  = self._max_drawdown(closes)
            report.volatility    = self._annualised_vol(returns)
            report.vol_regime    = self._classify_vol_regime(report.volatility)
            report.stress_loss   = self._stress_test(returns, market_df)
            report.market_beta   = self._compute_beta(returns, market_df)
            report.risk_score    = self._composite_risk_score(report)
            report.verdict       = self._verdict(report)
            report.reasoning     = self._build_reasoning(report)
            report.metadata      = {
                "n_bars":     len(closes),
                "return_mean": float(returns.mean()),
                "return_std":  float(returns.std()),
            }

        except Exception as exc:
            logger.exception("RiskAgent.analyse failed for %s: %s", symbol, exc)
            report.reasoning.append(f"Analysis error: {exc}")

        return report

    # ── Internal computations ─────────────────────────────────────────────────

    @staticmethod
    def _get_closes(df: pd.DataFrame) -> pd.Series:
        """Extract close prices from OHLCV (handles mixed case)."""
        for col in df.columns:
            if col.lower() == "close":
                return df[col].astype(float)
        # Fallback: last column
        return df.iloc[:, -1].astype(float)

    def _var(self, returns: pd.Series, confidence: float) -> float:
        """Historical VaR at given confidence level (returns negative value)."""
        if len(returns) < 5:
            return 0.0
        window = returns.tail(self.var_window)
        return float(np.percentile(window, (1 - confidence) * 100))

    def _cvar(self, returns: pd.Series, confidence: float) -> float:
        """Conditional VaR (Expected Shortfall) — mean of losses beyond VaR."""
        if len(returns) < 5:
            return 0.0
        var = self._var(returns, confidence)
        tail_losses = returns[returns <= var]
        if len(tail_losses) == 0:
            return var
        return float(tail_losses.mean())

    @staticmethod
    def _max_drawdown(closes: pd.Series) -> float:
        """Maximum drawdown from peak to trough."""
        rolling_max = closes.cummax()
        drawdown = (closes - rolling_max) / rolling_max
        return float(drawdown.min())

    def _annualised_vol(self, returns: pd.Series) -> float:
        """Annualised volatility (daily returns × √252)."""
        if len(returns) < 2:
            return 0.0
        return float(returns.std() * math.sqrt(252))

    def _classify_vol_regime(self, vol: float) -> str:
        if vol <= self.VOL_THRESHOLDS["LOW"]:
            return "LOW"
        elif vol <= self.VOL_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        elif vol <= self.VOL_THRESHOLDS["HIGH"]:
            return "HIGH"
        return "CRISIS"

    def _stress_test(
        self,
        returns: pd.Series,
        market_df: Optional[pd.DataFrame],
    ) -> float:
        """
        Apply historical shock scenarios and return worst-case loss.
        Uses beta to scale market shocks; falls back to percentile loss without market data.
        """
        beta = 1.0
        if market_df is not None:
            beta = self._compute_beta(returns, market_df)

        worst = 0.0
        for scenario in STRESS_SCENARIOS:
            asset_shock = scenario["market_drop"] * beta
            worst = min(worst, asset_shock)
        return float(worst)

    def _compute_beta(
        self,
        returns: pd.Series,
        market_df: Optional[pd.DataFrame],
    ) -> float:
        """Beta vs market index. Returns 1.0 if market data unavailable."""
        if market_df is None or len(market_df) < 20:
            return 1.0
        try:
            mkt_closes  = self._get_closes(market_df)
            mkt_returns = mkt_closes.pct_change().dropna()

            # Align on shared length
            n = min(len(returns), len(mkt_returns))
            r  = returns.values[-n:]
            m  = mkt_returns.values[-n:]

            cov_matrix = np.cov(r, m)
            if cov_matrix[1, 1] == 0:
                return 1.0
            return float(cov_matrix[0, 1] / cov_matrix[1, 1])
        except Exception:
            return 1.0

    @staticmethod
    def _composite_risk_score(r: RiskReport) -> float:
        """
        Composite risk score 0–1 (1 = safest, 0 = extreme risk).
        Weights: VaR (30%), MaxDD (30%), Vol (25%), Stress (15%)
        """
        # Normalise each metric to 0–1 (inverted — lower loss = higher score)
        def norm(val: float, worst: float, best: float) -> float:
            val   = max(worst, min(best, val))
            if best == worst:
                return 0.5
            return (val - worst) / (best - worst)

        var_score    = norm(r.var_95,       -0.15, -0.001)   # daily VaR
        dd_score     = norm(r.max_drawdown, -0.80, -0.05)
        vol_score    = norm(r.volatility,    0.80,  0.05)
        stress_score = norm(r.stress_loss,  -0.90, -0.05)

        return round(
            0.30 * var_score +
            0.30 * dd_score  +
            0.25 * vol_score +
            0.15 * stress_score,
            3,
        )

    @staticmethod
    def _verdict(r: RiskReport) -> str:
        """Translate risk score into actionable verdict."""
        if r.risk_score >= 0.72:
            return "BUY"
        elif r.risk_score >= 0.50:
            return "HOLD"
        elif r.risk_score >= 0.30:
            return "REDUCE"
        return "EXIT"

    def _build_reasoning(self, r: RiskReport) -> List[str]:
        lines = []
        lines.append(f"VaR(95%): {r.var_95:.2%}  |  CVaR(95%): {r.cvar_95:.2%}")
        lines.append(f"Max Drawdown: {r.max_drawdown:.2%}")
        lines.append(f"Annualised Vol: {r.volatility:.2%}  →  Regime: {r.vol_regime}")
        lines.append(f"Beta vs Market: {r.market_beta:.2f}")
        lines.append(f"Worst Stress Scenario: {r.stress_loss:.2%}")
        lines.append(f"Composite Risk Score: {r.risk_score:.3f}  →  Verdict: {r.verdict}")
        return lines
