"""
Run Backtest Tool
================

Allows ARIA to run historical simulations using Phase 11 Backtest Engine.
"""

from typing import Dict, Any
from atlas.assistants.aria.tools.base import Tool
from atlas.backtesting.backtest_engine import BacktestRunner

class RunBacktestTool(Tool):
    def __init__(self):
        super().__init__(
            name="run_backtest",
            description="Run a historical backtest for a strategy. Use this when the user asks to 'test', 'simulate', or 'verify' a strategy performance.",
            category="analysis"
        )
        self.add_parameter("strategy_name", "string", "Strategy to test (e.g., 'sma_crossover')")
        self.add_parameter("symbol", "string", "Asset symbol")
        self.add_parameter("timeframe", "string", "Time range (e.g., '1y')", required=False, default="1y")
        self.add_parameter("initial_capital", "number", "Starting capital", required=False, default=10000.0)
        
        self.runner = BacktestRunner()
        
    def execute(self, strategy_name: str, symbol: str, timeframe: str = "1y", initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Run a backtest.
        """
        try:
            print(f"🚀 Starting backtest for {strategy_name} on {symbol}...")
            results = self.runner.run(
                strategy=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital
            )
            # Ensure return is serializable
            if hasattr(results, 'summary'):
                return results.summary()
            return {"status": "completed", "results": str(results)}
        except Exception as e:
            return {"error": f"Backtest failed: {str(e)}"}
