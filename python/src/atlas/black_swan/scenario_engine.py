"""
Black Swan Scenario Engine
============================
Simulates historical and hypothetical catastrophic market events.
Produces portfolio impact analysis for each scenario.

Historical scenarios based on real events:
  - Black Monday (1987)
  - Asian Financial Crisis (1997)
  - LTCM / Russian Default (1998)
  - Dot-com Crash (2000-2002)
  - 9/11 Terror Attack (2001)
  - Global Financial Crisis (2008)
  - Flash Crash (2010)
  - European Debt Crisis (2011)
  - COVID Pandemic (2020)
  - Rate Shock (2022)

Hypothetical scenarios:
  - Geopolitical black swan (major conflict)
  - Cyber attack on financial infrastructure
  - Climate-triggered commodity shock
  - Stagflation + rate spiral

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.black_swan.scenario_engine")


# ══════════════════════════════════════════════════════════════════════════════
#  Scenario Definitions
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ScenarioDefinition:
    """Defines a market shock scenario."""
    name: str
    year: int
    category: str                      # HISTORICAL | HYPOTHETICAL
    equity_shock: float                # % change in broad equities
    vol_spike: float                   # VIX multiplier (e.g. 3.0 = VIX triples)
    duration_days: int                 # peak drawdown duration
    recovery_months: int               # months to recover
    credit_spread_bps: float           # investment grade spread widening in bps
    rate_change_bps: float             # 10Y treasury yield change in bps
    usd_change: float                  # USD index change %
    gold_change: float                 # Gold price change %
    oil_change: float                  # Oil price change %
    tech_multiplier: float             # tech sector relative to market
    financials_multiplier: float       # financials sector multiplier
    description: str = ""


HISTORICAL_SCENARIOS: List[ScenarioDefinition] = [
    ScenarioDefinition(
        name="Black Monday (1987)",
        year=1987, category="HISTORICAL",
        equity_shock=-0.227, vol_spike=5.0, duration_days=1,
        recovery_months=24, credit_spread_bps=150, rate_change_bps=-50,
        usd_change=-0.05, gold_change=+0.05, oil_change=-0.10,
        tech_multiplier=1.1, financials_multiplier=1.2,
        description="Largest single-day market crash (-22.6%). Program trading cascade.",
    ),
    ScenarioDefinition(
        name="Asian Financial Crisis (1997)",
        year=1997, category="HISTORICAL",
        equity_shock=-0.35, vol_spike=3.0, duration_days=180,
        recovery_months=36, credit_spread_bps=400, rate_change_bps=-100,
        usd_change=+0.10, gold_change=-0.05, oil_change=-0.30,
        tech_multiplier=0.8, financials_multiplier=1.5,
        description="EM currency crises cascade. Thailand baht devaluation triggered.",
    ),
    ScenarioDefinition(
        name="LTCM / Russia Default (1998)",
        year=1998, category="HISTORICAL",
        equity_shock=-0.20, vol_spike=3.5, duration_days=60,
        recovery_months=12, credit_spread_bps=500, rate_change_bps=-75,
        usd_change=-0.05, gold_change=+0.08, oil_change=-0.25,
        tech_multiplier=0.9, financials_multiplier=1.8,
        description="LTCM failure, Russian debt default. Liquidity crisis across markets.",
    ),
    ScenarioDefinition(
        name="Dot-com Crash (2000-2002)",
        year=2000, category="HISTORICAL",
        equity_shock=-0.49, vol_spike=2.5, duration_days=730,
        recovery_months=60, credit_spread_bps=200, rate_change_bps=-500,
        usd_change=+0.10, gold_change=+0.20, oil_change=-0.15,
        tech_multiplier=2.5, financials_multiplier=0.8,
        description="Nasdaq fell -78%. Valuation bubble burst in tech sector.",
    ),
    ScenarioDefinition(
        name="9/11 Terror Attack (2001)",
        year=2001, category="HISTORICAL",
        equity_shock=-0.14, vol_spike=4.0, duration_days=7,
        recovery_months=6, credit_spread_bps=100, rate_change_bps=-150,
        usd_change=-0.03, gold_change=+0.06, oil_change=+0.10,
        tech_multiplier=1.0, financials_multiplier=1.3,
        description="September 11 attacks. Market closed 4 days, opened -7% on reopen.",
    ),
    ScenarioDefinition(
        name="Global Financial Crisis (2008)",
        year=2008, category="HISTORICAL",
        equity_shock=-0.567, vol_spike=6.5, duration_days=517,
        recovery_months=60, credit_spread_bps=600, rate_change_bps=-400,
        usd_change=+0.15, gold_change=+0.25, oil_change=-0.55,
        tech_multiplier=0.9, financials_multiplier=2.0,
        description="Lehman Brothers collapse. S&P 500 lost 56.8% peak to trough.",
    ),
    ScenarioDefinition(
        name="Flash Crash (2010)",
        year=2010, category="HISTORICAL",
        equity_shock=-0.098, vol_spike=2.5, duration_days=1,
        recovery_months=1, credit_spread_bps=50, rate_change_bps=+10,
        usd_change=+0.02, gold_change=+0.02, oil_change=-0.10,
        tech_multiplier=1.0, financials_multiplier=1.1,
        description="Dow fell 1,000 points in minutes. HFT cascade, recovered same day.",
    ),
    ScenarioDefinition(
        name="COVID Pandemic (2020)",
        year=2020, category="HISTORICAL",
        equity_shock=-0.34, vol_spike=5.5, duration_days=33,
        recovery_months=5, credit_spread_bps=350, rate_change_bps=-150,
        usd_change=+0.08, gold_change=+0.08, oil_change=-0.70,
        tech_multiplier=0.6, financials_multiplier=1.3,
        description="Fastest 30%+ crash in history. Fed intervened massively.",
    ),
    ScenarioDefinition(
        name="Rate Shock (2022)",
        year=2022, category="HISTORICAL",
        equity_shock=-0.255, vol_spike=2.5, duration_days=270,
        recovery_months=18, credit_spread_bps=150, rate_change_bps=+450,
        usd_change=+0.15, gold_change=+0.00, oil_change=+0.40,
        tech_multiplier=1.6, financials_multiplier=0.7,
        description="Fed raised rates 475bps. Growth stocks collapsed (Nasdaq -33%).",
    ),
]

HYPOTHETICAL_SCENARIOS: List[ScenarioDefinition] = [
    ScenarioDefinition(
        name="Geopolitical Black Swan",
        year=2026, category="HYPOTHETICAL",
        equity_shock=-0.25, vol_spike=4.0, duration_days=30,
        recovery_months=12, credit_spread_bps=300, rate_change_bps=+100,
        usd_change=+0.05, gold_change=+0.20, oil_change=+0.50,
        tech_multiplier=1.0, financials_multiplier=1.2,
        description="Major geopolitical conflict disrupting global supply chains.",
    ),
    ScenarioDefinition(
        name="Cyber Attack on Financial Infrastructure",
        year=2026, category="HYPOTHETICAL",
        equity_shock=-0.20, vol_spike=5.0, duration_days=5,
        recovery_months=3, credit_spread_bps=400, rate_change_bps=-50,
        usd_change=-0.03, gold_change=+0.15, oil_change=-0.05,
        tech_multiplier=1.5, financials_multiplier=2.0,
        description="Coordinated attack on clearing houses/banking systems.",
    ),
    ScenarioDefinition(
        name="Stagflation + Rate Spiral",
        year=2026, category="HYPOTHETICAL",
        equity_shock=-0.40, vol_spike=3.0, duration_days=540,
        recovery_months=84, credit_spread_bps=250, rate_change_bps=+600,
        usd_change=+0.20, gold_change=+0.30, oil_change=+0.60,
        tech_multiplier=2.0, financials_multiplier=0.8,
        description="Persistent inflation forces rates to 8%+. Growth assets crushed.",
    ),
    ScenarioDefinition(
        name="Climate Commodity Shock",
        year=2026, category="HYPOTHETICAL",
        equity_shock=-0.18, vol_spike=2.5, duration_days=180,
        recovery_months=24, credit_spread_bps=200, rate_change_bps=+150,
        usd_change=0.0, gold_change=+0.10, oil_change=+0.80,
        tech_multiplier=0.9, financials_multiplier=1.0,
        description="Severe climate event disrupts food/energy commodity markets.",
    ),
]

ALL_SCENARIOS = HISTORICAL_SCENARIOS + HYPOTHETICAL_SCENARIOS


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    """Portfolio impact from a single scenario."""
    scenario_name: str
    category: str
    year: int
    portfolio_loss: float             # total portfolio % loss
    worst_asset: str                  # hardest hit asset
    worst_asset_loss: float
    best_asset: str                   # best hedge in scenario
    best_asset_gain: float
    recovery_estimate_months: int
    vol_at_peak: float                # estimated portfolio volatility at peak
    asset_impacts: Dict[str, float] = field(default_factory=dict)  # per-asset impact
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "scenario":              self.scenario_name,
            "category":              self.category,
            "year":                  self.year,
            "portfolio_loss":        round(self.portfolio_loss, 4),
            "worst_asset":           self.worst_asset,
            "worst_asset_loss":      round(self.worst_asset_loss, 4),
            "best_asset":            self.best_asset,
            "best_asset_gain":       round(self.best_asset_gain, 4),
            "recovery_months":       self.recovery_estimate_months,
            "vol_at_peak":           round(self.vol_at_peak, 4),
            "asset_impacts":         {k: round(v, 4) for k, v in self.asset_impacts.items()},
        }


@dataclass
class ScenarioReport:
    """Full scenario analysis across all scenarios."""
    n_scenarios: int
    worst_scenario: str
    worst_loss: float
    average_loss: float
    best_case_loss: float             # least bad scenario
    asset_names: List[str] = field(default_factory=list)
    results: List[ScenarioResult] = field(default_factory=list)
    heatmap: Optional[np.ndarray] = None   # (N_scenarios, N_assets) impact matrix

    def to_dict(self) -> Dict:
        return {
            "n_scenarios":   self.n_scenarios,
            "worst_scenario": self.worst_scenario,
            "worst_loss":     round(self.worst_loss, 4),
            "average_loss":   round(self.average_loss, 4),
            "best_case_loss": round(self.best_case_loss, 4),
            "results":        [r.to_dict() for r in self.results],
        }

    def summary(self) -> str:
        lines = [
            f"{'═'*60}",
            f"  BLACK SWAN SCENARIO REPORT — {self.n_scenarios} scenarios",
            f"{'─'*60}",
            f"  {'SCENARIO':<35} {'PORTFOLIO LOSS':>14}  {'RECOVERY':>8}",
            f"{'─'*60}",
        ]
        for r in sorted(self.results, key=lambda x: x.portfolio_loss):
            lines.append(
                f"  {r.scenario_name:<35} {r.portfolio_loss:>13.1%}  "
                f"{r.recovery_estimate_months:>7}m"
            )
        lines += [
            f"{'─'*60}",
            f"  Worst case:   {self.worst_scenario} ({self.worst_loss:.1%})",
            f"  Average loss: {self.average_loss:.1%}",
            f"  Best case:    {self.best_case_loss:.1%}",
            f"{'═'*60}",
        ]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  ScenarioEngine
# ══════════════════════════════════════════════════════════════════════════════

class ScenarioEngine:
    """
    Simulates portfolio impact under historical and hypothetical black swan scenarios.

    Uses each scenario's shock parameters to estimate per-asset and portfolio losses,
    accounting for sector composition, beta, and safe-haven allocations.

    Usage:
        engine = ScenarioEngine()
        report = engine.run_all(
            asset_names=["AAPL","SPY","GLD","TLT"],
            weights=[0.25, 0.50, 0.15, 0.10],
            betas={"AAPL": 1.25, "SPY": 1.0, "GLD": -0.15, "TLT": -0.45},
            sectors={"AAPL": "TECH", "SPY": "BROAD", "GLD": "SAFE_HAVEN", "TLT": "BONDS"},
        )
        print(report.summary())
    """

    # Asset type → base shock multiplier
    SECTOR_MULTIPLIERS: Dict[str, float] = {
        "TECH":       1.3,    # tech amplifies market shocks
        "FINANCIALS": 1.4,
        "ENERGY":     0.9,
        "HEALTH":     0.7,
        "CONSUMER":   0.8,
        "BROAD":      1.0,    # market ETF
        "SAFE_HAVEN": -0.3,   # inverse correlation
        "BONDS":      -0.4,
        "GOLD":       -0.2,
        "CASH":       0.0,
    }

    def __init__(self, scenarios: Optional[List[ScenarioDefinition]] = None):
        self.scenarios = scenarios or ALL_SCENARIOS
        logger.info("ScenarioEngine initialised with %d scenarios", len(self.scenarios))

    # ── Public API ────────────────────────────────────────────────────────────

    def run_all(
        self,
        asset_names: List[str],
        weights: List[float],
        betas: Optional[Dict[str, float]] = None,
        sectors: Optional[Dict[str, str]] = None,
        categories: Optional[List[str]] = None,
    ) -> ScenarioReport:
        """
        Run all scenarios against the portfolio.

        Parameters
        ----------
        asset_names : List of asset tickers/names
        weights     : Portfolio weights (must sum to ~1)
        betas       : {asset: beta} — market sensitivity. Defaults to 1.0.
        sectors     : {asset: sector} — sector classification. Defaults to 'BROAD'.
        categories  : Filter to specific categories ('HISTORICAL', 'HYPOTHETICAL')

        Returns ScenarioReport.
        """
        weights_arr = np.array(weights, dtype=float)
        weights_arr = weights_arr / weights_arr.sum()

        if betas is None:
            betas = {a: 1.0 for a in asset_names}
        if sectors is None:
            sectors = {a: "BROAD" for a in asset_names}

        scenarios = self.scenarios
        if categories:
            scenarios = [s for s in scenarios if s.category in categories]

        results: List[ScenarioResult] = []
        for scen in scenarios:
            result = self._run_single(scen, asset_names, weights_arr, betas, sectors)
            results.append(result)

        # Build heatmap
        heatmap = np.array([
            [r.asset_impacts.get(a, 0.0) for a in asset_names]
            for r in results
        ])

        losses = [r.portfolio_loss for r in results]
        worst_idx = int(np.argmin(losses))

        report = ScenarioReport(
            n_scenarios=len(results),
            worst_scenario=results[worst_idx].scenario_name,
            worst_loss=losses[worst_idx],
            average_loss=float(np.mean(losses)),
            best_case_loss=float(max(losses)),
            asset_names=asset_names,
            results=results,
            heatmap=heatmap,
        )

        logger.info(
            "ScenarioEngine: %d scenarios run. Worst: %s (%.1f%%)",
            len(results), report.worst_scenario, report.worst_loss * 100,
        )

        return report

    def run_single(
        self,
        scenario_name: str,
        asset_names: List[str],
        weights: List[float],
        betas: Optional[Dict[str, float]] = None,
        sectors: Optional[Dict[str, str]] = None,
    ) -> Optional[ScenarioResult]:
        """Run a single named scenario."""
        scen = next((s for s in self.scenarios if s.name == scenario_name), None)
        if scen is None:
            logger.warning("Scenario '%s' not found", scenario_name)
            return None

        weights_arr = np.array(weights, dtype=float)
        weights_arr = weights_arr / weights_arr.sum()

        if betas is None:
            betas = {a: 1.0 for a in asset_names}
        if sectors is None:
            sectors = {a: "BROAD" for a in asset_names}

        return self._run_single(scen, asset_names, weights_arr, betas, sectors)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_single(
        self,
        scen: ScenarioDefinition,
        assets: List[str],
        weights: np.ndarray,
        betas: Dict[str, float],
        sectors: Dict[str, str],
    ) -> ScenarioResult:
        """Calculate portfolio impact for one scenario."""
        asset_impacts = {}

        for i, asset in enumerate(assets):
            beta   = betas.get(asset, 1.0)
            sector = sectors.get(asset, "BROAD")
            impact = self._asset_impact(scen, beta, sector)
            asset_impacts[asset] = float(impact)

        # Portfolio loss = weighted sum of asset impacts
        portfolio_loss = float(sum(
            weights[i] * asset_impacts[assets[i]]
            for i in range(len(assets))
        ))

        worst_asset = min(asset_impacts, key=asset_impacts.get)  # type: ignore[arg-type]
        best_asset  = max(asset_impacts, key=asset_impacts.get)  # type: ignore[arg-type]

        # Peak volatility estimate
        vol_at_peak = abs(portfolio_loss) * scen.vol_spike / 3.0

        return ScenarioResult(
            scenario_name=scen.name,
            category=scen.category,
            year=scen.year,
            portfolio_loss=portfolio_loss,
            worst_asset=worst_asset,
            worst_asset_loss=asset_impacts[worst_asset],
            best_asset=best_asset,
            best_asset_gain=asset_impacts[best_asset],
            recovery_estimate_months=scen.recovery_months,
            vol_at_peak=vol_at_peak,
            asset_impacts=asset_impacts,
            metadata={
                "equity_shock": scen.equity_shock,
                "vol_spike":    scen.vol_spike,
                "duration":     scen.duration_days,
            },
        )

    def _asset_impact(
        self, scen: ScenarioDefinition, beta: float, sector: str
    ) -> float:
        """Compute impact on a single asset given scenario and asset characteristics."""
        # Base: market shock scaled by beta
        base_impact = scen.equity_shock * beta

        # Sector modifier
        sector_mult = self.SECTOR_MULTIPLIERS.get(sector, 1.0)

        # Tech / financial multipliers from scenario
        if sector == "TECH":
            sector_mult *= scen.tech_multiplier
        elif sector == "FINANCIALS":
            sector_mult *= scen.financials_multiplier

        # Safe havens and bonds use gold/rate changes instead
        if sector == "GOLD":
            return scen.gold_change
        if sector in ("BONDS", "SAFE_HAVEN"):
            # Bond price moves inversely with rates
            return -scen.rate_change_bps * 0.0008  # rough duration effect

        return float(base_impact * sector_mult)
