"""
Atlas — Core Validation Module
================================
Anti-overfitting framework for strategy validation.

Modules:
    pbo              — Probability of Backtest Overfitting
    walk_forward     — Walk-Forward Analysis
    cross_validation — Purged Cross-Validation for time series
    bootstrap_tests  — Bootstrap statistical significance tests

Usage:
    from atlas.core.validation import PBOAnalyzer, WalkForwardAnalyzer
    from atlas.core.validation import PurgedCrossValidator, BootstrapTests
    from atlas.core.validation import StrategyScorer

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .pbo import PBOAnalyzer, PBOResult
from .walk_forward import WalkForwardAnalyzer, WalkForwardResult
from .cross_validation import PurgedCrossValidator, CVFold
from .bootstrap_tests import BootstrapTests, BootstrapResult
from .scorer import StrategyScorer, StrategyScore

__all__ = [
    "PBOAnalyzer",
    "PBOResult",
    "WalkForwardAnalyzer",
    "WalkForwardResult",
    "PurgedCrossValidator",
    "CVFold",
    "BootstrapTests",
    "BootstrapResult",
    "StrategyScorer",
    "StrategyScore",
]
