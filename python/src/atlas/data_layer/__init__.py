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

from datetime import datetime

import pandas as pd

from atlas.data_layer.manager import DataManager
from atlas.data_layer.cache_store import CacheStore
from atlas.data_layer.normalize import add_returns, align_timeframe, normalize_ohlcv
from atlas.data_layer.quality.validator import DataValidator


def get_data(
    symbol: str,
    start: str,
    end: str,
    use_cache: bool = False,
    provider: str = "yahoo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Legacy convenience wrapper kept for backward compatibility.

    Returns OHLCV in the classic Atlas shape with capitalized columns:
    Open, High, Low, Close, Volume.
    """
    today = datetime.now().date()
    try:
        start_dt = datetime.fromisoformat(start).date()
        end_dt = datetime.fromisoformat(end).date()
    except ValueError as exc:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {exc}") from exc

    if start_dt > today and end_dt > today:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    manager = DataManager(
        default_provider=provider,
        enable_cache=use_cache,
        enable_validation=True,
    )
    df = manager.get_historical(
        symbol=symbol,
        start_date=start,
        end_date=end,
        interval=interval,
        provider=provider,
        use_cache=use_cache,
        add_returns_col=False,
    )

    if df is None or df.empty:
        raise ValueError(f"No data found for {symbol} between {start} and {end}")

    legacy_df = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    expected = ["Open", "High", "Low", "Close", "Volume"]
    for col in expected:
        if col not in legacy_df.columns:
            legacy_df[col] = pd.NA
    return legacy_df[expected]


__all__ = [
    "get_data",
    "DataManager",
    "normalize_ohlcv",
    "add_returns",
    "align_timeframe",
    "CacheStore",
    "DataValidator",
]
