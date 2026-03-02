"""
Atlas Data Layer
================
Central data ingestion, normalization, caching, and quality validation.

Usage:
    from atlas.data_layer import DataManager

    dm = DataManager()
    df = dm.get_historical("AAPL", "2024-01-01", "2024-12-31")

Copyright (c) 2026 M&C. All rights reserved.
"""

from atlas.data_layer.manager import DataManager
from atlas.data_layer.normalize import normalize_ohlcv, add_returns, align_timeframe
from atlas.data_layer.cache_store import CacheStore
from atlas.data_layer.quality.validator import DataValidator

__all__ = [
    "DataManager",
    "normalize_ohlcv",
    "add_returns",
    "align_timeframe",
    "CacheStore",
    "DataValidator",
]
