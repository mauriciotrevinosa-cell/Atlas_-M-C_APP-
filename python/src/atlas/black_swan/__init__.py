"""
Atlas Black Swan — Tail Risk & Catastrophe Modelling
======================================================
N-dimensional risk models for detecting and hedging extreme market events.

Inspired by:
  - ALADDIN (BlackRock) — multi-factor stress testing
  - Qlib — quantitative factor risk framework

Modules:
  n_dimensional_model  — Ledoit-Wolf covariance, PCA, fat-tail Monte Carlo,
                         Mahalanobis outlier detection, crisis correlation
  hedge_generator      — Hedge package generation (puts, inverse ETFs, safe havens)
  scenario_engine      — Historical + hypothetical scenario stress testing

Quick-start:
    import numpy as np
    from atlas.black_swan import NDimensionalBlackSwanModel, HedgeGenerator, ScenarioEngine

    # 1. Tail risk analysis
    model  = NDimensionalBlackSwanModel(n_simulations=50_000)
    result = model.analyse(returns_matrix, weights, asset_names=["AAPL","SPY","GLD"])
    print(result.summary())

    # 2. Hedge generation
    hedger  = HedgeGenerator()
    package = hedger.generate(result, portfolio_value=1_000_000)
    print(package.summary())

    # 3. Scenario stress test
    engine = ScenarioEngine()
    report = engine.run_all(
        asset_names=["AAPL","SPY","GLD"],
        weights=[0.40, 0.45, 0.15],
        betas={"AAPL": 1.2, "SPY": 1.0, "GLD": -0.15},
        sectors={"AAPL": "TECH", "SPY": "BROAD", "GLD": "GOLD"},
    )
    print(report.summary())

Copyright (c) 2026 M&C. All rights reserved.
"""

from .n_dimensional_model import (
    NDimensionalBlackSwanModel,
    TailRiskResult,
    PCAResult,
    PCARiskDecomposer,
    ledoit_wolf_shrinkage,
    mahalanobis_distance,
)
from .hedge_generator import (
    HedgeGenerator,
    HedgePackage,
    HedgeRecommendation,
    SAFE_HAVENS,
    INVERSE_ETFS,
    TAIL_INSTRUMENTS,
)
from .scenario_engine import (
    ScenarioEngine,
    ScenarioReport,
    ScenarioResult,
    ScenarioDefinition,
    HISTORICAL_SCENARIOS,
    HYPOTHETICAL_SCENARIOS,
    ALL_SCENARIOS,
)

__all__ = [
    # N-dimensional model
    "NDimensionalBlackSwanModel", "TailRiskResult", "PCAResult",
    "PCARiskDecomposer", "ledoit_wolf_shrinkage", "mahalanobis_distance",
    # Hedge generator
    "HedgeGenerator", "HedgePackage", "HedgeRecommendation",
    "SAFE_HAVENS", "INVERSE_ETFS", "TAIL_INSTRUMENTS",
    # Scenario engine
    "ScenarioEngine", "ScenarioReport", "ScenarioResult", "ScenarioDefinition",
    "HISTORICAL_SCENARIOS", "HYPOTHETICAL_SCENARIOS", "ALL_SCENARIOS",
]
