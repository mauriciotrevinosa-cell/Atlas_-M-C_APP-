"""
Analyze Risk Tool
=================

Assesses single-asset risk using the unified RiskEngine + DataManager.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from atlas.assistants.aria.tools.base import Tool
from atlas.assistants.aria.tools._data_utils import get_history_with_fallback
from atlas.data_layer.manager import DataManager
from atlas.risk.risk_engine import RiskEngine


class AnalyzeRiskTool(Tool):
    def __init__(self):
        super().__init__(
            name="analyze_risk",
            description=(
                "Assess risk for a symbol using VaR/CVaR, volatility, and leverage checks. "
                "Useful when the user asks about risk, safety, VaR, or leverage."
            ),
            category="analysis",
        )
        self.add_parameter("symbol", "string", "Asset symbol (e.g. BTC-USD, AAPL)")
        self.add_parameter(
            "amount",
            "number",
            "Position size in dollars (used for VaR dollar estimate)",
            required=False,
            default=1000.0,
        )
        self.add_parameter(
            "leverage",
            "number",
            "Leverage used (1.0 = spot)",
            required=False,
            default=1.0,
        )
        self.add_parameter(
            "timeframe",
            "string",
            "Lookback window for risk estimation",
            required=False,
            default="3mo",
        )

        self.risk_engine = RiskEngine()
        self.data_manager = DataManager()

    def execute(
        self,
        symbol: str,
        amount: float = 1000.0,
        leverage: float = 1.0,
        timeframe: str = "3mo",
        **_: Any,
    ) -> Dict[str, Any]:
        """
        Analyze risk for a potential trade.
        """
        try:
            ticker = symbol.strip().upper()
            data, synthetic = get_history_with_fallback(
                self.data_manager,
                ticker,
                timeframe,
            )

            close_col = "close" if "close" in data.columns else "Close"
            returns = pd.to_numeric(data[close_col], errors="coerce").pct_change().dropna()
            if returns.empty:
                return {"error": f"Insufficient return history for {ticker}", "symbol": ticker}

            var_block = self.risk_engine.var.historical_var(
                returns=returns,
                confidence=0.95,
                horizon_days=1,
            )

            last_price = float(data[close_col].iloc[-1])
            lev = max(float(leverage), 1.0)

            liq_price = self.risk_engine.liquidation.calculate_liquidation_price(
                entry=last_price,
                leverage=lev,
                side="long",
            )
            # Assume a conservative 3% protective stop to estimate safe leverage.
            safe_lev = self.risk_engine.liquidation.safe_leverage(
                entry=last_price,
                stop_loss=last_price * 0.97,
                side="long",
                buffer_pct=0.02,
            )

            var_pct = float(var_block.get("var", 0.0))
            cvar_pct = float(var_block.get("cvar", 0.0))
            annual_vol = float(returns.std() * (252 ** 0.5))

            risk_flags = []
            if lev > safe_lev:
                risk_flags.append(
                    f"Leverage {lev:.1f}x exceeds conservative safe leverage {safe_lev:.1f}x."
                )
            if var_pct > 0.03:
                risk_flags.append(f"High 1-day VaR ({var_pct:.2%}).")
            if annual_vol > 0.5:
                risk_flags.append(f"Elevated annualized volatility ({annual_vol:.1%}).")

            return {
                "symbol": ticker,
                "timeframe": timeframe,
                "price": round(last_price, 4),
                "leverage": round(lev, 2),
                "position_amount_usd": round(float(amount), 2),
                "var_95_1d_pct": round(var_pct * 100, 3),
                "cvar_95_1d_pct": round(cvar_pct * 100, 3),
                "var_95_1d_usd": round(float(amount) * var_pct, 2),
                "cvar_95_1d_usd": round(float(amount) * cvar_pct, 2),
                "annualized_volatility_pct": round(annual_vol * 100, 2),
                "liquidation_price_est": round(float(liq_price), 4),
                "suggested_max_leverage": round(float(safe_lev), 2),
                "is_safe_to_trade": len(risk_flags) == 0,
                "risk_flags": risk_flags,
                "source": "synthetic_local" if synthetic else "provider",
                "synthetic": bool(synthetic),
                "note": "Metrics are historical/statistical and not guaranteed forecasts.",
            }
        except Exception as e:
            return {"error": f"Risk analysis failed: {str(e)}", "symbol": symbol}
