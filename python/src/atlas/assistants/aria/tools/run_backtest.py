"""
Run Backtest Tool
=================

Runs a lightweight historical backtest using Atlas BacktestRunner.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

import numpy as np
import pandas as pd

from atlas.assistants.aria.tools.base import Tool
from atlas.assistants.aria.tools._data_utils import get_history_with_fallback
from atlas.backtesting.backtest_engine import BacktestRunner
from atlas.data_layer.manager import DataManager


class RunBacktestTool(Tool):
    def __init__(self):
        super().__init__(
            name="run_backtest",
            description=(
                "Run a historical backtest for a strategy. "
                "Useful when asked to test, simulate, or verify strategy performance."
            ),
            category="analysis",
        )
        self.add_parameter("strategy_name", "string", "Strategy to test (e.g., sma_crossover)")
        self.add_parameter("symbol", "string", "Asset symbol")
        self.add_parameter("timeframe", "string", "Time range (e.g., 1y)", required=False, default="1y")
        self.add_parameter(
            "initial_capital",
            "number",
            "Starting capital",
            required=False,
            default=10000.0,
        )

        self.data_manager = DataManager()

    def _make_strategy(self, strategy_name: str) -> Callable[[pd.Series, dict | None, dict], str | None]:
        name = (strategy_name or "").strip().lower()
        if not name:
            name = "sma_crossover"

        if name in {"sma", "sma_cross", "sma_crossover", "trend_following"}:
            fast, slow = 10, 30

            def _sma_strategy(row: pd.Series, position: dict | None, context: dict) -> str | None:
                history = context.setdefault("_close_hist", [])
                close = float(row["close"])
                history.append(close)
                if len(history) < slow + 1:
                    return None

                fast_ma = float(np.mean(history[-fast:]))
                slow_ma = float(np.mean(history[-slow:]))
                prev_fast = float(np.mean(history[-fast - 1:-1]))
                prev_slow = float(np.mean(history[-slow - 1:-1]))

                crossed_up = prev_fast <= prev_slow and fast_ma > slow_ma
                crossed_down = prev_fast >= prev_slow and fast_ma < slow_ma

                if position is None:
                    if crossed_up:
                        return "long"
                    if crossed_down:
                        return "short"
                    return None

                if position["side"] == "long" and crossed_down:
                    return "close"
                if position["side"] == "short" and crossed_up:
                    return "close"
                return None

            return _sma_strategy

        if name in {"mean_reversion", "mr"}:
            window = 20
            entry_z = 1.3
            exit_z = 0.2

            def _mr_strategy(row: pd.Series, position: dict | None, context: dict) -> str | None:
                history = context.setdefault("_close_hist", [])
                close = float(row["close"])
                history.append(close)
                if len(history) < window:
                    return None

                arr = np.array(history[-window:], dtype=float)
                mu = float(arr.mean())
                sigma = float(arr.std())
                if sigma <= 1e-12:
                    return None
                z = (close - mu) / sigma

                if position is None:
                    if z <= -entry_z:
                        return "long"
                    if z >= entry_z:
                        return "short"
                    return None

                if abs(z) <= exit_z:
                    return "close"
                return None

            return _mr_strategy

        # Fallback to SMA strategy for unknown names.
        return self._make_strategy("sma_crossover")

    def execute(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str = "1y",
        initial_capital: float = 10000.0,
        **_: Any,
    ) -> Dict[str, Any]:
        """
        Run a backtest.
        """
        try:
            ticker = symbol.strip().upper()
            data, synthetic = get_history_with_fallback(
                self.data_manager,
                ticker,
                timeframe,
            )

            # BacktestRunner expects lower-case OHLCV.
            required = ("open", "high", "low", "close", "volume")
            if any(col not in data.columns for col in required):
                return {"error": f"Missing OHLCV columns for {ticker}", "symbol": ticker}
            df = data[list(required)].dropna().copy()
            if len(df) < 30:
                return {"error": f"Not enough bars for backtest ({len(df)})", "symbol": ticker}

            strategy_fn = self._make_strategy(strategy_name)
            runner = BacktestRunner(
                strategy_fn=strategy_fn,
                initial_capital=float(initial_capital),
                commission_pct=0.001,
                slippage_pct=0.0005,
            )
            result = runner.run(df)
            metrics = result.get("metrics", {})

            return {
                "symbol": ticker,
                "strategy": strategy_name,
                "timeframe": timeframe,
                "bars_tested": int(len(df)),
                "initial_capital": round(float(initial_capital), 2),
                "final_capital": result.get("final_capital"),
                "total_trades": result.get("total_trades"),
                "source": "synthetic_local" if synthetic else "provider",
                "synthetic": bool(synthetic),
                "metrics": metrics,
                "trades": result.get("trades", []),
                "summary": {
                    "total_return_pct": metrics.get("total_return_pct"),
                    "sharpe_ratio": metrics.get("sharpe_ratio"),
                    "max_drawdown_pct": metrics.get("max_drawdown_pct"),
                    "win_rate": metrics.get("win_rate"),
                },
            }
        except Exception as e:
            return {"error": f"Backtest failed: {str(e)}", "symbol": symbol}
