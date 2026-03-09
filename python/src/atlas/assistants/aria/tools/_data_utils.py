"""
Utilities for ARIA tools that need market data with offline fallback.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import numpy as np
import pandas as pd

from atlas.data_layer.manager import DataManager


_BARS_BY_TIMEFRAME = {
    "5d": 5,
    "1mo": 21,
    "3mo": 63,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
    "ytd": 180,
    "max": 1500,
}


def _seed_for(symbol: str, timeframe: str) -> int:
    token = f"{symbol.upper()}::{timeframe.lower()}".encode("utf-8")
    return int(hashlib.sha256(token).hexdigest()[:8], 16)


def _synth_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    n = _BARS_BY_TIMEFRAME.get(timeframe.lower(), 252)
    rng = np.random.default_rng(_seed_for(symbol, timeframe))

    base_price = float(rng.uniform(20.0, 300.0))
    annual_vol = float(rng.uniform(0.15, 0.45))
    daily_sigma = annual_vol / np.sqrt(252)
    daily_mu = float(rng.uniform(-0.0002, 0.0008))

    closes = [base_price]
    for _ in range(n - 1):
        ret = rng.normal(daily_mu, daily_sigma)
        closes.append(closes[-1] * np.exp(ret))
    close = np.array(closes, dtype=float)

    spread = rng.uniform(0.0025, 0.015, size=n)
    high = close * (1 + spread)
    low = close * (1 - spread)
    open_ = np.concatenate([[close[0]], close[:-1]]) * rng.uniform(0.997, 1.003, size=n)
    open_ = np.clip(open_, low, high)
    volume = rng.integers(80_000, 3_000_000, size=n, dtype=np.int64)

    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def get_history_with_fallback(
    data_manager: DataManager,
    symbol: str,
    timeframe: str,
) -> Tuple[pd.DataFrame, bool]:
    """
    Return OHLCV data and a `synthetic` flag.
    """
    try:
        df = data_manager.get_historical(symbol, timeframe=timeframe)
    except Exception:
        df = pd.DataFrame()
    if df is not None and not df.empty:
        return df, False
    return _synth_ohlcv(symbol, timeframe), True
