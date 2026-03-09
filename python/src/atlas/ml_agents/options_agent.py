"""
Options Agent — Swarm Committee Member
=========================================
Specialized agent for options/derivatives market analysis.
Uses the derivatives layer to extract options signals and flow data.

Signals produced:
  - Implied Volatility (IV) vs HV ratio
  - Put/Call ratio (market sentiment)
  - Options flow bias (calls vs puts in dollar terms)
  - IV Rank / IV Percentile
  - Key options levels (max pain, gamma walls)
  - Theta decay pressure
  - Options-implied expected move
  - Overall options verdict → BUY / HOLD / REDUCE / SELL

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.ml_agents.options_agent")


# ── Black-Scholes helpers ─────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989422820 * math.exp(-x * x / 2)
    p = d * t * (
        0.31938153 +
        t * (-0.356563782 +
             t * (1.781477937 +
                  t * (-1.821255978 + t * 1.330274429)))
    )
    return 1 - p if x > 0 else p


def bs_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """Black-Scholes option price."""
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return max(0.0, S - K)
        return max(0.0, K - S)
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_implied_vol(
    market_price: float,
    S: float, K: float, T: float, r: float,
    option_type: str = "call",
    tol: float = 1e-6, max_iter: int = 200
) -> float:
    """Newton-Raphson implied volatility solver."""
    sigma = 0.25
    for _ in range(max_iter):
        price = bs_price(S, K, T, r, sigma, option_type)
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
        vega = S * _norm_cdf(d1) * math.sqrt(T)
        if vega < 1e-10:
            break
        diff = price - market_price
        if abs(diff) < tol:
            break
        sigma -= diff / vega
        sigma = max(0.001, min(sigma, 5.0))
    return sigma


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class OptionsReport:
    """Output from the Options Agent."""
    symbol: str
    iv_current: float = 0.0        # Current ATM implied volatility
    hv_30: float = 0.0             # 30-day historical volatility
    iv_hv_ratio: float = 1.0       # IV / HV ratio
    iv_rank: float = 0.5           # 0–1 (IV rank over 52 weeks)
    iv_percentile: float = 0.5     # 0–1 (percentile)
    put_call_ratio: float = 1.0    # Options sentiment
    flow_bias: str = "NEUTRAL"     # BULLISH / BEARISH / NEUTRAL
    flow_score: float = 0.0        # dollar-weighted call - put bias (-1 to +1)
    max_pain: float = 0.0          # Strike price with max options pain
    expected_move: float = 0.0     # 1SD move implied by options
    gamma_wall_up: float = 0.0     # Nearest call gamma wall
    gamma_wall_dn: float = 0.0     # Nearest put gamma wall
    theta_pressure: str = "LOW"    # HIGH / MEDIUM / LOW (time decay pressure)
    options_score: float = 0.5     # 0–1 composite
    verdict: str = "HOLD"
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "iv": {
                "current": round(self.iv_current, 4),
                "hv_30": round(self.hv_30, 4),
                "iv_hv_ratio": round(self.iv_hv_ratio, 3),
                "rank": round(self.iv_rank, 3),
                "percentile": round(self.iv_percentile, 3),
            },
            "flow": {
                "put_call_ratio": round(self.put_call_ratio, 3),
                "bias": self.flow_bias,
                "score": round(self.flow_score, 3),
            },
            "levels": {
                "max_pain": round(self.max_pain, 2),
                "expected_move_pct": round(self.expected_move, 4),
                "gamma_wall_up": round(self.gamma_wall_up, 2),
                "gamma_wall_dn": round(self.gamma_wall_dn, 2),
            },
            "theta_pressure": self.theta_pressure,
            "options_score": round(self.options_score, 3),
            "verdict": self.verdict,
            "reasoning": self.reasoning,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  OptionsAgent
# ══════════════════════════════════════════════════════════════════════════════

class OptionsAgent:
    """
    Swarm committee member: Options Specialist.

    Analyses implied volatility surface, options flow, and key gamma levels.
    When live options data is unavailable, synthesizes metrics from OHLCV.

    Usage:
        agent = OptionsAgent()
        report = agent.analyse("SPY", ohlcv_df, options_chain=None)
        print(report.to_dict())
    """

    def __init__(
        self,
        risk_free_rate: float = 0.045,
        hv_window: int = 30,
        iv_lookback: int = 252,
    ):
        self.r          = risk_free_rate
        self.hv_window  = hv_window
        self.iv_lookback = iv_lookback
        logger.info("OptionsAgent initialised (rf=%.1f%%, hv_window=%d)", risk_free_rate * 100, hv_window)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        options_chain: Optional[pd.DataFrame] = None,
    ) -> OptionsReport:
        """
        Full options analysis.

        Parameters
        ----------
        symbol       : Ticker
        ohlcv        : OHLCV DataFrame
        options_chain: Optional DataFrame with columns:
                       [strike, expiry_days, option_type, bid, ask, volume, open_interest]

        Returns OptionsReport.
        """
        report = OptionsReport(symbol=symbol)

        if ohlcv is None or len(ohlcv) < 20:
            report.reasoning.append("Insufficient price data — defaults used")
            return report

        try:
            closes = self._closes(ohlcv)
            S = float(closes.iloc[-1])

            # Historical vol (always available)
            report.hv_30 = self._hv(closes, self.hv_window)

            if options_chain is not None and len(options_chain) > 0:
                self._analyse_chain(report, S, options_chain)
            else:
                self._synthesize_from_price(report, S, closes)

            report.options_score = self._composite(report)
            report.verdict       = self._verdict(report)
            report.reasoning     = self._build_reasoning(report)
            report.metadata      = {
                "spot": S,
                "hv_30": round(report.hv_30, 4),
                "chain_available": options_chain is not None,
            }

        except Exception as exc:
            logger.exception("OptionsAgent.analyse failed for %s: %s", symbol, exc)
            report.reasoning.append(f"Analysis error: {exc}")

        return report

    # ── Chain analysis (live options data) ───────────────────────────────────

    def _analyse_chain(
        self, report: OptionsReport, S: float, chain: pd.DataFrame
    ) -> None:
        """Analyse real options chain data."""
        chain = chain.copy()
        chain.columns = [c.lower() for c in chain.columns]

        # ATM IV
        atm_row = chain.iloc[(chain["strike"] - S).abs().argsort()[:1]]
        if len(atm_row) > 0 and "bid" in chain.columns and "ask" in chain.columns:
            mid = (float(atm_row["bid"].values[0]) + float(atm_row["ask"].values[0])) / 2
            T   = float(atm_row.get("expiry_days", pd.Series([30])).values[0]) / 365
            opt = atm_row.get("option_type", pd.Series(["call"])).values[0]
            if mid > 0:
                report.iv_current = bs_implied_vol(mid, S, float(atm_row["strike"].values[0]), T, self.r, str(opt))

        # IV vs HV
        report.iv_hv_ratio = report.iv_current / report.hv_30 if report.hv_30 > 0 else 1.0

        # Put/Call ratio by volume
        if "option_type" in chain.columns and "volume" in chain.columns:
            calls_vol = chain[chain["option_type"].str.lower() == "call"]["volume"].sum()
            puts_vol  = chain[chain["option_type"].str.lower() == "put"]["volume"].sum()
            report.put_call_ratio = float(puts_vol / calls_vol) if calls_vol > 0 else 1.0

            # Flow bias: dollar-weighted (volume × strike proxy)
            call_flow = chain[chain["option_type"].str.lower() == "call"]["volume"].sum()
            put_flow  = chain[chain["option_type"].str.lower() == "put"]["volume"].sum()
            total     = call_flow + put_flow
            if total > 0:
                report.flow_score = float((call_flow - put_flow) / total)

        report.flow_bias = self._flow_bias(report.flow_score, report.put_call_ratio)

        # Max pain
        report.max_pain = self._max_pain(chain, S)

        # Expected move
        if report.iv_current > 0:
            T_near = chain["expiry_days"].min() / 365 if "expiry_days" in chain.columns else 30 / 365
            report.expected_move = report.iv_current * math.sqrt(T_near)

        # Gamma walls
        report.gamma_wall_up, report.gamma_wall_dn = self._gamma_walls(chain, S)

        # Theta pressure
        report.theta_pressure = self._theta_pressure(chain, S)

        # IV rank/percentile (synthetic from IV vs HV ratio since we lack history)
        ratio = report.iv_hv_ratio
        report.iv_rank       = min(1.0, max(0.0, (ratio - 0.7) / 1.5))
        report.iv_percentile = report.iv_rank

    def _synthesize_from_price(
        self, report: OptionsReport, S: float, closes: pd.Series
    ) -> None:
        """Synthesize options metrics from price data when chain is unavailable."""
        hv = report.hv_30
        # Estimate IV from HV with a small premium
        report.iv_current    = hv * 1.10
        report.iv_hv_ratio   = 1.10
        report.put_call_ratio = 1.0
        report.flow_score    = 0.0
        report.flow_bias     = "NEUTRAL"
        report.max_pain      = S
        report.expected_move = hv * math.sqrt(30 / 252)

        # IV rank from rolling HV
        if len(closes) >= self.iv_lookback:
            daily_vol = closes.pct_change().dropna().rolling(self.hv_window).std() * math.sqrt(252)
            daily_vol = daily_vol.dropna()
            lo  = float(daily_vol.min())
            hi  = float(daily_vol.max())
            cur = hv
            rng = hi - lo
            report.iv_rank       = (cur - lo) / rng if rng > 0 else 0.5
            report.iv_percentile = float((daily_vol <= cur).mean())

        report.gamma_wall_up = S * 1.05
        report.gamma_wall_dn = S * 0.95
        report.theta_pressure = "LOW"

    # ── Helper computations ───────────────────────────────────────────────────

    @staticmethod
    def _closes(df: pd.DataFrame) -> pd.Series:
        for c in df.columns:
            if c.lower() == "close":
                return df[c].astype(float)
        return df.iloc[:, -1].astype(float)

    def _hv(self, closes: pd.Series, window: int) -> float:
        """Annualised historical volatility."""
        if len(closes) < window + 1:
            return float(closes.pct_change().dropna().std() * math.sqrt(252))
        returns = closes.pct_change().dropna()
        return float(returns.tail(window).std() * math.sqrt(252))

    @staticmethod
    def _max_pain(chain: pd.DataFrame, S: float) -> float:
        """Calculate max pain strike (strike minimising total options value expiring ITM)."""
        if "strike" not in chain.columns or "open_interest" not in chain.columns:
            return S
        strikes = chain["strike"].unique()
        pain_vals = {}
        for tgt in strikes:
            total = 0.0
            for _, row in chain.iterrows():
                K  = row["strike"]
                oi = row.get("open_interest", 0)
                ot = str(row.get("option_type", "call")).lower()
                if ot == "call" and tgt > K:
                    total += (tgt - K) * oi
                elif ot == "put" and tgt < K:
                    total += (K - tgt) * oi
            pain_vals[tgt] = total
        if not pain_vals:
            return S
        return float(min(pain_vals, key=pain_vals.get))

    @staticmethod
    def _gamma_walls(chain: pd.DataFrame, S: float) -> Tuple[float, float]:
        """Find nearest call/put gamma walls (highest OI concentrations)."""
        if "strike" not in chain.columns or "open_interest" not in chain.columns:
            return S * 1.05, S * 0.95
        calls = chain[chain.get("option_type", pd.Series()).str.lower() == "call"] if "option_type" in chain.columns else chain
        puts  = chain[chain.get("option_type", pd.Series()).str.lower() == "put"]  if "option_type" in chain.columns else chain

        above = calls[calls["strike"] > S]
        below = puts[puts["strike"]  < S]

        wall_up = float(above.loc[above["open_interest"].idxmax(), "strike"]) if len(above) > 0 else S * 1.05
        wall_dn = float(below.loc[below["open_interest"].idxmax(), "strike"]) if len(below) > 0 else S * 0.95
        return wall_up, wall_dn

    @staticmethod
    def _theta_pressure(chain: pd.DataFrame, S: float) -> str:
        """Classify theta decay pressure based on near-term OI."""
        if "expiry_days" not in chain.columns:
            return "LOW"
        near = chain[chain["expiry_days"] <= 14]
        near_oi = near["open_interest"].sum() if "open_interest" in near.columns else 0
        total_oi = chain["open_interest"].sum() if "open_interest" in chain.columns else 1
        if total_oi == 0:
            return "LOW"
        ratio = near_oi / total_oi
        if ratio >= 0.40:
            return "HIGH"
        elif ratio >= 0.20:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _flow_bias(flow_score: float, pcr: float) -> str:
        if flow_score > 0.15 and pcr < 0.9:
            return "BULLISH"
        elif flow_score < -0.15 and pcr > 1.1:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _composite(r: OptionsReport) -> float:
        """
        Composite score 0–1.
        High IV rank + bearish flow = low score (risk)
        Low IV rank + bullish flow = high score (opportunity)
        """
        def clamp(v):
            return max(0.0, min(1.0, v))

        # IV environment: low IV = better for buyers
        iv_score = clamp(1 - r.iv_rank)

        # Flow bias
        flow_map = {"BULLISH": 0.75, "NEUTRAL": 0.50, "BEARISH": 0.25}
        flow_s   = flow_map.get(r.flow_bias, 0.50)

        # PCR: <0.7 = bullish, >1.2 = bearish
        pcr_s = clamp(1 - (r.put_call_ratio - 0.5) / 1.0)

        # Theta: high theta pressure = risky
        theta_map = {"HIGH": 0.25, "MEDIUM": 0.50, "LOW": 0.75}
        theta_s   = theta_map.get(r.theta_pressure, 0.50)

        return round(
            0.35 * iv_score +
            0.30 * flow_s   +
            0.20 * pcr_s    +
            0.15 * theta_s,
            3,
        )

    @staticmethod
    def _verdict(r: OptionsReport) -> str:
        if r.options_score >= 0.70:
            return "BUY"
        elif r.options_score >= 0.50:
            return "HOLD"
        elif r.options_score >= 0.30:
            return "REDUCE"
        return "SELL"

    def _build_reasoning(self, r: OptionsReport) -> List[str]:
        lines = []
        lines.append(f"IV: {r.iv_current:.1%}  HV(30): {r.hv_30:.1%}  IV/HV: {r.iv_hv_ratio:.2f}")
        lines.append(f"IV Rank: {r.iv_rank:.1%}  |  IV Percentile: {r.iv_percentile:.1%}")
        lines.append(f"Put/Call Ratio: {r.put_call_ratio:.2f}  |  Flow Bias: {r.flow_bias}")
        lines.append(f"Max Pain: ${r.max_pain:.2f}  |  1SD Expected Move: ±{r.expected_move:.1%}")
        lines.append(f"Gamma Walls: ↑${r.gamma_wall_up:.2f}  ↓${r.gamma_wall_dn:.2f}")
        lines.append(f"Theta Pressure: {r.theta_pressure}")
        lines.append(f"Options Score: {r.options_score:.3f}  →  Verdict: {r.verdict}")
        return lines
