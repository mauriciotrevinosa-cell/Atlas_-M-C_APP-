"""
Volatility Analysis — Phase 2.2
Measures historical volatility and classifies volatility regime.
Uses ATR and rolling standard deviation (HV).
"""
import pandas as pd
import numpy as np
from enum import Enum


class VolRegime(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class VolatilityAnalyzer:
    """
    Computes volatility metrics and classifies regime.

    Output:
        {
            'hv_20': 0.23,             # 20-day historical vol (annualized %)
            'hv_60': 0.19,
            'atr_pct': 1.8,            # ATR as % of current price
            'regime': VolRegime.HIGH,
            'percentile': 75,          # HV percentile vs last 252 days
            'description': 'High volatility — HV20=23%'
        }
    """

    def __init__(self, hv_window: int = 20, atr_period: int = 14, annualize: bool = True):
        self.hv_window = hv_window
        self.atr_period = atr_period
        self.annualize = annualize

    def _atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data["high"], data["low"], data["close"]
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def analyze(self, data: pd.DataFrame) -> dict:
        """
        Analyze volatility from OHLCV DataFrame.

        Args:
            data: Normalized OHLCV DataFrame

        Returns:
            Volatility metrics dict
        """
        returns = data["close"].pct_change().dropna()

        factor = np.sqrt(252) if self.annualize else 1.0

        hv_20 = returns.rolling(20).std().iloc[-1] * factor
        hv_60 = returns.rolling(60).std().iloc[-1] * factor if len(data) >= 60 else hv_20

        atr_series = self._atr(data)
        atr_value = atr_series.iloc[-1]
        atr_pct = (atr_value / data["close"].iloc[-1]) * 100

        # Percentile of current HV vs last 252 bars
        hv_rolling = returns.rolling(self.hv_window).std() * factor
        valid_hv = hv_rolling.dropna()
        tail = valid_hv.iloc[-252:] if len(valid_hv) >= 252 else valid_hv
        percentile = float((tail < hv_20).mean() * 100) if len(tail) > 0 else 50.0

        # Regime classification
        if percentile >= 85:
            regime = VolRegime.EXTREME
        elif percentile >= 65:
            regime = VolRegime.HIGH
        elif percentile <= 25:
            regime = VolRegime.LOW
        else:
            regime = VolRegime.NORMAL

        return {
            "hv_20": round(float(hv_20) * 100, 2) if not pd.isna(hv_20) else 0.0,
            "hv_60": round(float(hv_60) * 100, 2) if not pd.isna(hv_60) else 0.0,
            "atr": round(float(atr_value), 4) if not pd.isna(atr_value) else 0.0,
            "atr_pct": round(float(atr_pct), 2) if not pd.isna(atr_pct) else 0.0,
            "percentile": round(percentile, 1),
            "regime": regime,
            "description": f"{regime.value} volatility — HV20={hv_20*100:.1f}%, pct={percentile:.0f}th",
        }
