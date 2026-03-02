"""
Market State Detection Module

Detects and classifies market regimes to inform trading decisions.

Regimes:
- Trending (up/down)
- Ranging (sideways)
- Volatile (high vol)
- Calm (low vol)

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .regime import RegimeDetector
from .volatility import VolatilityRegime
from .internals import MarketInternals
from .sentiment import SentimentAnalyzer

__all__ = [
    'RegimeDetector',
    'VolatilityRegime',
    'MarketInternals',
    'SentimentAnalyzer'
]
