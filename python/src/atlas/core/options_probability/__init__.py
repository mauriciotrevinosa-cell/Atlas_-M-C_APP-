"""
Atlas — Options Probability Engine
=====================================
Derives price probability distributions from live options market data.

Modules:
    engine        — OptionsProbabilityEngine (main interface)
    iv_surface    — ImpliedVolatilitySurface (term structure + skew)
    distribution  — RiskNeutralDistribution (probability density from options)
    fetcher       — OptionsChainFetcher (yfinance-based options data)

Usage:
    from atlas.core.options_probability import OptionsProbabilityEngine
    result = engine.analyze("SPY")

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .engine import OptionsProbabilityEngine, OptionsProbabilityResult
from .iv_surface import ImpliedVolatilitySurface, IVSurfacePoint
from .distribution import RiskNeutralDistribution, PriceDistribution
from .fetcher import OptionsChainFetcher, OptionsChain

__all__ = [
    "OptionsProbabilityEngine",
    "OptionsProbabilityResult",
    "ImpliedVolatilitySurface",
    "IVSurfacePoint",
    "RiskNeutralDistribution",
    "PriceDistribution",
    "OptionsChainFetcher",
    "OptionsChain",
]
