"""
Atlas — System Models
=======================
Theoretical models for probabilistic market analysis.

Modules:
    utility_functions  — StrategyUtility: U(strategy) = f(return, risk, cost, uncertainty)
    constraint_engine  — ConstraintEngine: liquidity, volatility, regime constraints
    probabilistic_state — ProbabilisticStateModel: multi-state market probability

These models provide the mathematical backbone for treating markets as
complex systems operating under uncertainty and constraints.

Usage:
    from atlas.core.system_models import StrategyUtility, ConstraintEngine
    from atlas.core.system_models import ProbabilisticStateModel

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .utility_functions import StrategyUtility, StrategyUtilityResult
from .constraint_engine import ConstraintEngine, ConstraintSet, ConstraintViolation
from .probabilistic_state import ProbabilisticStateModel, MarketState, StateDistribution

__all__ = [
    "StrategyUtility",
    "StrategyUtilityResult",
    "ConstraintEngine",
    "ConstraintSet",
    "ConstraintViolation",
    "ProbabilisticStateModel",
    "MarketState",
    "StateDistribution",
]
