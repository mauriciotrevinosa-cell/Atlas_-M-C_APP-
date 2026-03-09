"""
Hedge Generator — Black Swan Protection
=========================================
Generates defensive hedge recommendations based on tail-risk analysis.

Given a portfolio and its black swan risk profile, suggests:
  1. Protective puts (individual + index)
  2. Inverse ETF positions
  3. Volatility instruments (VIX calls)
  4. Safe haven allocations (Gold, Treasuries)
  5. Cross-asset hedges (currency, commodity)
  6. Portfolio delta/gamma neutralisation

Each hedge is sized based on the portfolio's VaR contribution
and the cost-effectiveness of the hedge.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .n_dimensional_model import TailRiskResult

logger = logging.getLogger("atlas.black_swan.hedge_generator")


# ── Hedge Instruments ─────────────────────────────────────────────────────────

# Inverse ETFs by category
INVERSE_ETFS = {
    "BROAD_MARKET": ["SH", "SDS", "SPXS"],   # S&P 500 inverse (1x, 2x, 3x)
    "NASDAQ":       ["PSQ", "QID", "SQQQ"],
    "FINANCIALS":   ["SEF", "FAZ"],
    "ENERGY":       ["DDG", "DUG"],
    "REAL_ESTATE":  ["REK", "SRS"],
}

# Safe haven allocations
SAFE_HAVENS = {
    "GOLD":       {"ticker": "GLD",  "description": "Gold ETF",              "crisis_beta": -0.15},
    "T_BONDS":    {"ticker": "TLT",  "description": "20+ Year Treasury ETF", "crisis_beta": -0.40},
    "TIPS":       {"ticker": "TIP",  "description": "Inflation-Protected",   "crisis_beta": -0.20},
    "YEN":        {"ticker": "FXY",  "description": "Japanese Yen ETF",      "crisis_beta": -0.30},
    "CHF":        {"ticker": "FXF",  "description": "Swiss Franc ETF",       "crisis_beta": -0.25},
    "VIX_CALLS":  {"ticker": "UVXY", "description": "VIX Volatility ETF",    "crisis_beta": -0.80},
}

# Tail hedging instruments
TAIL_INSTRUMENTS = {
    "SPY_PUTS":    {"description": "S&P 500 Protective Puts",  "leverage": 1.0,  "cost_pct": 0.02},
    "QQQ_PUTS":    {"description": "Nasdaq Protective Puts",   "leverage": 1.0,  "cost_pct": 0.025},
    "VIX_CALLS":   {"description": "VIX Call Spread",          "leverage": 5.0,  "cost_pct": 0.015},
    "TAIL_ETF":    {"description": "Cambria Tail Risk ETF",    "leverage": 1.0,  "cost_pct": 0.008},
    "CASH":        {"description": "Cash / Money Market",      "leverage": 1.0,  "cost_pct": 0.0},
}


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class HedgeRecommendation:
    """Individual hedge instrument recommendation."""
    instrument: str
    ticker: str
    description: str
    allocation_pct: float         # % of portfolio to allocate
    expected_payoff_pct: float    # expected % gain in crash scenario
    cost_pct: float               # annual cost as % of portfolio
    hedge_type: str               # TAIL / INVERSE / SAFE_HAVEN / VOLATILITY / CASH
    priority: int                 # 1=highest priority
    rationale: str = ""

    def to_dict(self) -> Dict:
        return {
            "instrument":       self.instrument,
            "ticker":           self.ticker,
            "description":      self.description,
            "allocation_pct":   round(self.allocation_pct, 3),
            "expected_payoff":  round(self.expected_payoff_pct, 3),
            "cost_pct":         round(self.cost_pct, 4),
            "hedge_type":       self.hedge_type,
            "priority":         self.priority,
            "rationale":        self.rationale,
        }


@dataclass
class HedgePackage:
    """Complete hedge package for a portfolio."""
    portfolio_value: float
    tail_risk_score: float           # 0 = extreme risk, 1 = safe
    hedge_level: str                 # MINIMAL / MODERATE / AGGRESSIVE / CRISIS
    total_hedge_allocation_pct: float
    total_hedge_cost_pct: float
    expected_portfolio_protection: float  # % loss avoided in crash scenario
    recommendations: List[HedgeRecommendation] = field(default_factory=list)
    risk_reduction: float = 0.0          # % reduction in expected tail loss
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "portfolio_value":         self.portfolio_value,
            "tail_risk_score":         round(self.tail_risk_score, 3),
            "hedge_level":             self.hedge_level,
            "total_allocation_pct":    round(self.total_hedge_allocation_pct, 3),
            "total_cost_pct":          round(self.total_hedge_cost_pct, 4),
            "expected_protection_pct": round(self.expected_portfolio_protection, 3),
            "risk_reduction_pct":      round(self.risk_reduction, 3),
            "recommendations":         [r.to_dict() for r in self.recommendations],
            "reasoning":               self.reasoning,
        }

    def summary(self) -> str:
        lines = [
            f"{'═'*55}",
            f"  HEDGE PACKAGE — Level: {self.hedge_level}",
            f"  Portfolio: ${self.portfolio_value:,.0f}  |  Risk Score: {self.tail_risk_score:.2f}",
            f"{'─'*55}",
        ]
        for i, rec in enumerate(self.recommendations, 1):
            lines.append(
                f"  {i}. [{rec.ticker:<8}] {rec.description[:30]:<30} "
                f"{rec.allocation_pct*100:>5.1f}%  (cost {rec.cost_pct*100:.2f}%/yr)"
            )
        lines += [
            f"{'─'*55}",
            f"  Total Hedge:   {self.total_hedge_allocation_pct*100:.1f}% of portfolio",
            f"  Annual Cost:   {self.total_hedge_cost_pct*100:.2f}%",
            f"  Protection:    {self.expected_portfolio_protection*100:.1f}% of tail losses covered",
            f"  Risk Reduction:{self.risk_reduction*100:.1f}%",
            f"{'═'*55}",
        ]
        for r in self.reasoning:
            lines.append(f"  • {r}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  HedgeGenerator
# ══════════════════════════════════════════════════════════════════════════════

class HedgeGenerator:
    """
    Generates defensive hedge recommendations from a TailRiskResult.

    Hedge intensity scales with tail risk severity:
      VaR99 > -20%  → CRISIS    hedge (20-35% portfolio)
      VaR99 > -10%  → AGGRESSIVE hedge (10-20%)
      VaR99 > -5%   → MODERATE  hedge (5-10%)
      otherwise     → MINIMAL   hedge (1-5%)

    Usage:
        model   = NDimensionalBlackSwanModel()
        result  = model.analyse(returns_matrix)
        hedger  = HedgeGenerator()
        package = hedger.generate(result, portfolio_value=1_000_000)
        print(package.summary())
    """

    # Hedge intensity thresholds (portfolio % allocation)
    HEDGE_LEVELS = {
        "CRISIS":     (0.20, 0.35),
        "AGGRESSIVE": (0.10, 0.20),
        "MODERATE":   (0.05, 0.10),
        "MINIMAL":    (0.01, 0.05),
    }

    def __init__(self, max_hedge_cost_pct: float = 0.03):
        """
        Parameters
        ----------
        max_hedge_cost_pct : Maximum acceptable annual hedge cost (% of portfolio)
        """
        self.max_hedge_cost = max_hedge_cost_pct
        logger.info("HedgeGenerator initialised (max_cost=%.1f%%/yr)", max_hedge_cost_pct * 100)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        tail_result: TailRiskResult,
        portfolio_value: float = 1_000_000,
        include_volatility: bool = True,
        include_safe_havens: bool = True,
    ) -> HedgePackage:
        """
        Generate a complete hedge package.

        Parameters
        ----------
        tail_result       : Output from NDimensionalBlackSwanModel.analyse()
        portfolio_value   : Portfolio value in dollars
        include_volatility: Include VIX/volatility instruments
        include_safe_havens: Include gold, bonds, FX

        Returns HedgePackage.
        """
        # Determine hedge level from VaR99
        var99 = tail_result.portfolio_var_99
        hedge_level = self._hedge_level(var99)
        alloc_range = self.HEDGE_LEVELS[hedge_level]

        # Tail risk score (0=very risky, 1=safe)
        tail_score  = self._tail_score(var99, tail_result.worst_01pct)

        package = HedgePackage(
            portfolio_value=portfolio_value,
            tail_risk_score=tail_score,
            hedge_level=hedge_level,
            total_hedge_allocation_pct=0.0,
            total_hedge_cost_pct=0.0,
            expected_portfolio_protection=0.0,
        )

        # Build recommendations
        recs: List[HedgeRecommendation] = []
        budget = alloc_range[1]   # start at max of range

        # 1. Tail hedges (highest priority)
        recs.extend(self._tail_hedges(budget, hedge_level, var99))

        # 2. Inverse ETFs (for directional shorts)
        if hedge_level in ("CRISIS", "AGGRESSIVE"):
            recs.extend(self._inverse_etfs(budget * 0.3, tail_result))

        # 3. Safe havens
        if include_safe_havens:
            recs.extend(self._safe_haven_allocs(budget * 0.4, hedge_level))

        # 4. Volatility instruments
        if include_volatility and hedge_level in ("CRISIS", "AGGRESSIVE"):
            recs.extend(self._volatility_instruments(budget * 0.15))

        # Assign priorities and filter by cost budget
        recs = self._prioritise(recs)
        recs = self._filter_by_cost(recs)

        package.recommendations = recs
        package.total_hedge_allocation_pct = sum(r.allocation_pct for r in recs)
        package.total_hedge_cost_pct       = sum(
            r.allocation_pct * r.cost_pct for r in recs
        )
        package.expected_portfolio_protection = self._expected_protection(recs, var99)
        package.risk_reduction = self._risk_reduction(recs, tail_result)
        package.reasoning      = self._reasoning(package, tail_result)
        package.metadata       = {
            "var99": var99,
            "cvar99": tail_result.portfolio_cvar_99,
            "crisis_loss": tail_result.crisis_correlation_loss,
        }

        logger.info(
            "HedgePackage[%s]: %d instruments, %.1f%% allocation, %.2f%% cost",
            hedge_level, len(recs),
            package.total_hedge_allocation_pct * 100,
            package.total_hedge_cost_pct * 100,
        )

        return package

    # ── Recommendation builders ───────────────────────────────────────────────

    def _tail_hedges(
        self, budget: float, level: str, var99: float
    ) -> List[HedgeRecommendation]:
        recs = []

        # SPY puts — core tail hedge
        spy_alloc = budget * 0.35
        recs.append(HedgeRecommendation(
            instrument="SPY_PUTS",
            ticker="SPY",
            description="S&P 500 Protective Puts (5% OTM, 3M)",
            allocation_pct=spy_alloc,
            expected_payoff_pct=abs(var99) * 0.7,
            cost_pct=TAIL_INSTRUMENTS["SPY_PUTS"]["cost_pct"],
            hedge_type="TAIL",
            priority=1,
            rationale=f"Core tail hedge — protects against >{abs(var99):.0%} drawdowns",
        ))

        # Cambria TAIL ETF — systematic tail risk
        if level in ("CRISIS", "AGGRESSIVE", "MODERATE"):
            tail_alloc = budget * 0.20
            recs.append(HedgeRecommendation(
                instrument="TAIL_ETF",
                ticker="TAIL",
                description="Cambria Tail Risk ETF (systematic)",
                allocation_pct=tail_alloc,
                expected_payoff_pct=abs(var99) * 0.5,
                cost_pct=TAIL_INSTRUMENTS["TAIL_ETF"]["cost_pct"],
                hedge_type="TAIL",
                priority=2,
                rationale="Low-cost systematic tail hedge — pays in extreme drawdowns",
            ))

        return recs

    def _inverse_etfs(
        self, budget: float, result: TailRiskResult
    ) -> List[HedgeRecommendation]:
        recs = []
        # Use simple inverse ETF (SH not SDS to avoid leverage decay)
        alloc = budget * 0.5
        recs.append(HedgeRecommendation(
            instrument="SH",
            ticker="SH",
            description="ProShares Short S&P 500 (1x inverse)",
            allocation_pct=alloc,
            expected_payoff_pct=0.15,
            cost_pct=0.0089,
            hedge_type="INVERSE",
            priority=3,
            rationale="Broad market short — directional protection without leverage decay",
        ))
        return recs

    @staticmethod
    def _safe_haven_allocs(budget: float, level: str) -> List[HedgeRecommendation]:
        recs = []

        # Gold
        gold_alloc = budget * 0.35
        recs.append(HedgeRecommendation(
            instrument="GOLD",
            ticker="GLD",
            description="Gold ETF — crisis safe haven",
            allocation_pct=gold_alloc,
            expected_payoff_pct=0.10,
            cost_pct=0.0040,
            hedge_type="SAFE_HAVEN",
            priority=4,
            rationale="Gold historically appreciates during equity crises",
        ))

        # Long-duration Treasuries
        tlt_alloc = budget * 0.40
        recs.append(HedgeRecommendation(
            instrument="TLT",
            ticker="TLT",
            description="20+ Year Treasury ETF — flight-to-safety",
            allocation_pct=tlt_alloc,
            expected_payoff_pct=0.12,
            cost_pct=0.0015,
            hedge_type="SAFE_HAVEN",
            priority=4,
            rationale="Negative equity-bond correlation provides diversification",
        ))

        return recs

    @staticmethod
    def _volatility_instruments(budget: float) -> List[HedgeRecommendation]:
        recs = []
        recs.append(HedgeRecommendation(
            instrument="VIX_CALLS",
            ticker="UVXY",
            description="VIX / Volatility Spike Hedge",
            allocation_pct=budget,
            expected_payoff_pct=1.5,   # high leverage in VIX spikes
            cost_pct=TAIL_INSTRUMENTS["VIX_CALLS"]["cost_pct"],
            hedge_type="VOLATILITY",
            priority=2,
            rationale="VIX spikes 5-10x in market crashes — high leverage payoff",
        ))
        return recs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _hedge_level(var99: float) -> str:
        if var99 <= -0.20:
            return "CRISIS"
        elif var99 <= -0.10:
            return "AGGRESSIVE"
        elif var99 <= -0.05:
            return "MODERATE"
        return "MINIMAL"

    @staticmethod
    def _tail_score(var99: float, worst_01: float) -> float:
        """0 = extreme risk, 1 = very safe."""
        var_score   = max(0, min(1, (var99 + 0.30) / 0.30))
        worst_score = max(0, min(1, (worst_01 + 0.60) / 0.60))
        return round(0.6 * var_score + 0.4 * worst_score, 3)

    @staticmethod
    def _prioritise(recs: List[HedgeRecommendation]) -> List[HedgeRecommendation]:
        return sorted(recs, key=lambda r: (r.priority, -r.expected_payoff_pct))

    def _filter_by_cost(
        self, recs: List[HedgeRecommendation]
    ) -> List[HedgeRecommendation]:
        """Keep hedges within annual cost budget."""
        kept, running_cost = [], 0.0
        for rec in recs:
            item_cost = rec.allocation_pct * rec.cost_pct
            if running_cost + item_cost <= self.max_hedge_cost:
                kept.append(rec)
                running_cost += item_cost
        return kept

    @staticmethod
    def _expected_protection(
        recs: List[HedgeRecommendation], var99: float
    ) -> float:
        """Estimate % of tail loss offset by hedge payoffs."""
        total_payoff = sum(r.allocation_pct * r.expected_payoff_pct for r in recs)
        if var99 == 0:
            return 0.0
        return min(1.0, total_payoff / abs(var99))

    @staticmethod
    def _risk_reduction(
        recs: List[HedgeRecommendation], result: TailRiskResult
    ) -> float:
        """Estimate reduction in portfolio VaR from hedges."""
        hedge_alloc = sum(r.allocation_pct for r in recs)
        # Rough approximation: hedge provides proportional VaR reduction
        return min(0.80, hedge_alloc * 2.0)  # cap at 80% reduction

    @staticmethod
    def _reasoning(package: HedgePackage, result: TailRiskResult) -> List[str]:
        lines = []
        lines.append(
            f"Tail risk level: {package.hedge_level} "
            f"(VaR99={result.portfolio_var_99:.1%}, worst 0.1%={result.worst_01pct:.1%})"
        )
        if result.crisis_correlation_loss < -0.20:
            lines.append(
                f"Crisis correlation scenario shows {result.crisis_correlation_loss:.1%} loss "
                f"— diversification breaks down in crashes"
            )
        if package.total_hedge_allocation_pct > 0.15:
            lines.append("High allocation to hedges — consider reducing portfolio risk concentration instead")
        lines.append(
            f"Annual hedge cost: {package.total_hedge_cost_pct*100:.2f}% "
            f"vs expected tail protection of {package.expected_portfolio_protection*100:.0f}%"
        )
        return lines
