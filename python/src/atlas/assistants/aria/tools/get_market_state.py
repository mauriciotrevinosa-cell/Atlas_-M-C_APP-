"""
Get Market State Tool for ARIA
==============================

Analyzes regime + volatility using Atlas `market_state` package.
"""

from __future__ import annotations

from typing import Any, Dict

from atlas.assistants.aria.tools.base import Tool
from atlas.assistants.aria.tools._data_utils import get_history_with_fallback
from atlas.data_layer.manager import DataManager
from atlas.market_state import RegimeDetector, VolatilityRegime


class GetMarketStateTool(Tool):
    """
    Tool for analyzing market state (regime + volatility).
    """

    def __init__(self):
        super().__init__(
            name="get_market_state",
            description="Analyze market regime (trend/range/volatility) for a symbol.",
            category="analysis",
        )
        self.add_parameter(
            "symbol",
            "string",
            "Ticker symbol (e.g., AAPL, SPY, BTC-USD)",
            required=True,
        )
        self.add_parameter(
            "period",
            "string",
            "Analysis period (e.g., '1y', '6mo', 'ytd')",
            required=False,
            default="1y",
        )

        self.dm = DataManager()

    def execute(self, symbol: str, period: str = "1y", **_: Any) -> Dict[str, Any]:
        """
        Execute market state analysis.
        """
        try:
            ticker = symbol.strip().upper()
            df, synthetic = get_history_with_fallback(self.dm, ticker, period)

            # market_state package expects capitalized OHLCV.
            cap = df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            ).copy()
            required = ("Open", "High", "Low", "Close", "Volume")
            if any(col not in cap.columns for col in required):
                return {"error": f"Missing OHLCV columns for {ticker}", "symbol": ticker}
            cap = cap[list(required)]

            lookback = max(20, min(252, len(cap)))
            detector = RegimeDetector(adx_threshold=25.0, lookback=min(lookback, 60))
            regime_state = detector.detect(cap)

            vol = VolatilityRegime(lookback=lookback)
            vol_regime = vol.classify(cap)
            vol_forecast = vol.get_volatility_forecast(cap, horizon=5)

            adx_value = float(regime_state.metrics.get("adx", 0.0))
            description = (
                f"{ticker} is in {regime_state.regime} regime "
                f"(confidence {regime_state.confidence:.1%}, ADX {adx_value:.2f}) "
                f"with {vol_regime} volatility."
            )

            return {
                "symbol": ticker,
                "period": period,
                "bars": int(len(cap)),
                "current_regime": str(regime_state.regime),
                "regime_confidence": round(float(regime_state.confidence) * 100, 2),
                "trend_strength": round(adx_value, 4),
                "volatility_regime": str(vol_regime),
                "volatility_forecast_annualized": round(float(vol_forecast), 6),
                "source": "synthetic_local" if synthetic else "provider",
                "synthetic": bool(synthetic),
                "description": description,
            }
        except Exception as e:
            return {"error": str(e), "symbol": symbol}
