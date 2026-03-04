"""
Atlas — Automated Signal Discovery
=====================================
Scans historical data to discover statistically significant trading signals.

Modules:
    engine          — SignalDiscoveryEngine (main orchestrator)
    pattern_scanner — PatternScanner (candlestick + price pattern mining)
    correlation     — CorrelationFinder (lead-lag & cross-asset correlations)
    feature_ranker  — FeatureRanker (ranks predictive features by importance)

Usage:
    from atlas.core.signal_discovery import SignalDiscoveryEngine
    signals = engine.discover(data, max_signals=20)

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .engine import SignalDiscoveryEngine, DiscoveredSignal, DiscoveryReport
from .pattern_scanner import PatternScanner, PatternResult
from .correlation import CorrelationFinder, CorrelationResult
from .feature_ranker import FeatureRanker, FeatureImportance

__all__ = [
    "SignalDiscoveryEngine",
    "DiscoveredSignal",
    "DiscoveryReport",
    "PatternScanner",
    "PatternResult",
    "CorrelationFinder",
    "CorrelationResult",
    "FeatureRanker",
    "FeatureImportance",
]
