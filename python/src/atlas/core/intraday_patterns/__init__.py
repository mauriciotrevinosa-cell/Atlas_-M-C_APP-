"""
Atlas — Intraday Pattern Engine
==================================
Detects intraday behavioral patterns for short-term edge.

Modules:
    engine         — IntradayPatternEngine (main interface)
    gap_analyzer   — GapAnalyzer (gap-up/down continuation)
    opening_drive  — OpeningDriveDetector (first-bar momentum)
    session_model  — SessionVolatilityModel (time-of-day volatility profile)

Usage:
    from atlas.core.intraday_patterns import IntradayPatternEngine
    result = engine.analyze(data, symbol="AAPL")

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .engine import IntradayPatternEngine, IntradayPattern, IntradayReport
from .gap_analyzer import GapAnalyzer, GapEvent, GapType
from .opening_drive import OpeningDriveDetector, OpeningDriveSignal
from .session_model import SessionVolatilityModel, SessionProfile

__all__ = [
    "IntradayPatternEngine",
    "IntradayPattern",
    "IntradayReport",
    "GapAnalyzer",
    "GapEvent",
    "GapType",
    "OpeningDriveDetector",
    "OpeningDriveSignal",
    "SessionVolatilityModel",
    "SessionProfile",
]
