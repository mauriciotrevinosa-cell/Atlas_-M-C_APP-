"""
Atlas — Whale Detection Engine
================================
Detects large institutional participant activity using volume, price,
and options flow signals.

Modules:
    engine        — WhaleDetectionEngine (main interface)
    volume        — VolumeAnomalyDetector (unusual volume spikes)
    flow          — InstitutionalFlowTracker (block trades, dark pool proxy)
    options_flow  — UnusualOptionsActivity (large options contracts)

Usage:
    from atlas.core.whale_detection import WhaleDetectionEngine
    signals = engine.analyze(data, symbol="AAPL")

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .engine import WhaleDetectionEngine, WhaleSignal, WhaleReport
from .volume import VolumeAnomalyDetector, VolumeAnomaly
from .flow import InstitutionalFlowTracker, FlowSignal
from .options_flow import UnusualOptionsActivity, OptionsFlowSignal

__all__ = [
    "WhaleDetectionEngine",
    "WhaleSignal",
    "WhaleReport",
    "VolumeAnomalyDetector",
    "VolumeAnomaly",
    "InstitutionalFlowTracker",
    "FlowSignal",
    "UnusualOptionsActivity",
    "OptionsFlowSignal",
]
