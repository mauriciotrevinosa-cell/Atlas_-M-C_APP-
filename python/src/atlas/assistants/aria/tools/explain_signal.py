"""
Explain Signal Tool
===================

Generates a directional view + explanation using the ARIA Trader composite scorer.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from atlas.assistants.aria.tools.base import Tool
from atlas.assistants.aria.tools._data_utils import get_history_with_fallback
from atlas.data_layer.manager import DataManager
from atlas.trader.composite_scorer import CompositeScorer


class ExplainSignalTool(Tool):
    def __init__(self):
        super().__init__(
            name="explain_signal",
            description=(
                "Generate and explain a trading signal for an asset. "
                "Useful for 'should I buy/sell?' and directional analysis."
            ),
            category="analysis",
        )
        self.add_parameter("symbol", "string", "Asset symbol to analyze")
        self.add_parameter(
            "timeframe",
            "string",
            "Historical window used for analysis",
            required=False,
            default="6mo",
        )

        self.data_manager = DataManager()
        self.scorer = CompositeScorer()

    def execute(
        self,
        symbol: str,
        timeframe: str = "6mo",
        **_: Any,
    ) -> Dict[str, Any]:
        """
        Generate a signal and explain the reasoning.
        """
        try:
            ticker = symbol.strip().upper()
            data, synthetic = get_history_with_fallback(
                self.data_manager,
                ticker,
                timeframe,
            )

            # CompositeScorer expects capitalized OHLCV.
            rename_map = {
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
            df = data.rename(columns=rename_map).copy()
            for col in ("Open", "High", "Low", "Close", "Volume"):
                if col not in df.columns:
                    return {"error": f"Missing required column '{col}' for {ticker}", "asset": ticker}
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)

            result = self.scorer.score(ticker, df, info={})
            payload = result.to_dict()

            verdict = payload.get("verdict", "HOLD")
            action = "HOLD"
            if "BUY" in verdict:
                action = "BUY"
            elif "SELL" in verdict or "AVOID" in verdict:
                action = "SELL"

            reasoning_lines = []
            for line in payload.get("insights", []):
                reasoning_lines.append(f"- {line}")
            if payload.get("risk_flags"):
                reasoning_lines.append("Risk flags:")
                for flag in payload["risk_flags"]:
                    reasoning_lines.append(f"- {flag}")

            return {
                "asset": ticker,
                "timeframe": timeframe,
                "action": action,
                "confidence": payload.get("confidence"),
                "verdict": verdict,
                "composite_score": payload.get("composite_score"),
                "reasoning": "\n".join(reasoning_lines) if reasoning_lines else "No detailed analysis available.",
                "conflicts": payload.get("risk_flags", []),
                "components": payload.get("components", []),
                "prediction": payload.get("prediction"),
                "source": "synthetic_local" if synthetic else "provider",
                "synthetic": bool(synthetic),
                "raw": payload,
            }
        except Exception as e:
            return {"error": f"Signal generation failed: {str(e)}", "asset": symbol}
