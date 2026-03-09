"""
Candlestick Pattern Recognition — Phase 3.1
Detects: Doji, Hammer, Shooting Star, Engulfing (Bullish/Bearish)
"""
import pandas as pd
import numpy as np


def _body_size(row) -> float:
    return abs(row["close"] - row["open"])


def _upper_wick(row) -> float:
    return row["high"] - max(row["open"], row["close"])


def _lower_wick(row) -> float:
    return min(row["open"], row["close"]) - row["low"]


def _candle_range(row) -> float:
    return row["high"] - row["low"]


class CandlePatterns:
    """
    Scans OHLCV DataFrame for known candlestick patterns.
    Returns a DataFrame of signals (1=bullish, -1=bearish, 0=none) per pattern.
    """

    def __init__(self, doji_threshold: float = 0.1, wick_ratio: float = 2.0):
        """
        Args:
            doji_threshold: Body/range ratio below which a candle is a Doji (default 10%)
            wick_ratio: Minimum wick/body ratio for Hammer/Shooting Star (default 2x)
        """
        self.doji_threshold = doji_threshold
        self.wick_ratio = wick_ratio

    def scan(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Scan all candles for patterns.

        Returns:
            DataFrame with columns: doji, hammer, shooting_star, bullish_engulfing, bearish_engulfing
            Values: 1 (bullish signal), -1 (bearish signal), 0 (no pattern)
        """
        results = pd.DataFrame(index=data.index)
        results["doji"] = self._doji(data)
        results["hammer"] = self._hammer(data)
        results["shooting_star"] = self._shooting_star(data)
        results["bullish_engulfing"] = self._bullish_engulfing(data)
        results["bearish_engulfing"] = self._bearish_engulfing(data)

        # Composite signal (any bullish vs bearish pattern)
        bullish_mask = (results[["hammer", "bullish_engulfing"]] == 1).any(axis=1)
        bearish_mask = (results[["shooting_star", "bearish_engulfing"]] == -1).any(axis=1)
        results["composite"] = 0
        results.loc[bullish_mask, "composite"] = 1
        results.loc[bearish_mask, "composite"] = -1

        return results

    def _doji(self, data: pd.DataFrame) -> pd.Series:
        """Doji: body very small relative to total range — indecision."""
        def is_doji(row):
            rng = _candle_range(row)
            if rng == 0:
                return 0
            return 0 if _body_size(row) / rng > self.doji_threshold else -1  # neutral/indecision

        return data.apply(is_doji, axis=1)

    def _hammer(self, data: pd.DataFrame) -> pd.Series:
        """Hammer: small body at top, long lower wick — bullish reversal."""
        def is_hammer(row):
            body = _body_size(row)
            lower = _lower_wick(row)
            upper = _upper_wick(row)
            rng = _candle_range(row)
            if rng == 0 or body == 0:
                return 0
            # Long lower wick, small upper wick, body in upper 1/3
            if lower >= self.wick_ratio * body and upper <= body * 0.3:
                return 1
            return 0

        return data.apply(is_hammer, axis=1)

    def _shooting_star(self, data: pd.DataFrame) -> pd.Series:
        """Shooting Star: small body at bottom, long upper wick — bearish reversal."""
        def is_shooting_star(row):
            body = _body_size(row)
            lower = _lower_wick(row)
            upper = _upper_wick(row)
            if body == 0:
                return 0
            if upper >= self.wick_ratio * body and lower <= body * 0.3:
                return -1
            return 0

        return data.apply(is_shooting_star, axis=1)

    def _bullish_engulfing(self, data: pd.DataFrame) -> pd.Series:
        """Bullish Engulfing: bearish candle followed by larger bullish candle."""
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(data)):
            prev = data.iloc[i - 1]
            curr = data.iloc[i]
            prev_bearish = prev["close"] < prev["open"]
            curr_bullish = curr["close"] > curr["open"]
            engulfs = curr["open"] <= prev["close"] and curr["close"] >= prev["open"]
            if prev_bearish and curr_bullish and engulfs:
                signals.iloc[i] = 1
        return signals

    def _bearish_engulfing(self, data: pd.DataFrame) -> pd.Series:
        """Bearish Engulfing: bullish candle followed by larger bearish candle."""
        signals = pd.Series(0, index=data.index)
        for i in range(1, len(data)):
            prev = data.iloc[i - 1]
            curr = data.iloc[i]
            prev_bullish = prev["close"] > prev["open"]
            curr_bearish = curr["close"] < curr["open"]
            engulfs = curr["open"] >= prev["close"] and curr["close"] <= prev["open"]
            if prev_bullish and curr_bearish and engulfs:
                signals.iloc[i] = -1
        return signals

    def latest_patterns(self, data: pd.DataFrame, lookback: int = 5) -> list:
        """
        Return a list of patterns detected in the last N candles.

        Returns:
            List of dicts: [{'pattern': 'hammer', 'signal': 1, 'bar': -1}, ...]
        """
        results = self.scan(data)
        tail = results.iloc[-lookback:]
        patterns = []
        for col in ["doji", "hammer", "shooting_star", "bullish_engulfing", "bearish_engulfing"]:
            for idx, val in tail[col].items():
                if val != 0:
                    bar_offset = results.index.get_loc(idx) - (len(results) - 1)
                    patterns.append({
                        "pattern": col,
                        "signal": int(val),
                        "bar_offset": bar_offset,
                        "date": str(idx),
                    })
        return sorted(patterns, key=lambda x: x["bar_offset"], reverse=True)
