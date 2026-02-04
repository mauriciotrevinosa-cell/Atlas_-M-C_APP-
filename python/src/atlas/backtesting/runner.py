import pandas as pd
from atlas.core_intelligence.signal_engine import SignalEngine
import numpy as np

class BacktestRunner:
    """
    Phase 6: Backtesting Engine.
    Simulates execution of SignalEngine over historical data.
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.signal_engine = SignalEngine()

    def run(self, data: pd.DataFrame, strategy: str = "trend_following"):
        """
        Run backtest.
        Returns dict with metrics and equity curve.
        """
        # 1. Get Signals
        signals = self.signal_engine.evaluate(data, strategy)
        
        # 2. Simulate Trades (Vectorized for MVP)
        # Shift signal by 1 to avoid lookahead bias (trade on NEXT open)
        positions = signals['signal'].shift(1)
        
        # Calculate daily returns
        market_returns = data['close'].pct_change()
        strategy_returns = positions * market_returns
        
        # Equity Curve
        equity_curve = (1 + strategy_returns).cumprod() * self.initial_capital
        
        # Metrics
        total_return = (equity_curve.iloc[-1] - self.initial_capital) / self.initial_capital
        sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() != 0 else 0
        
        return {
            "final_equity": float(round(equity_curve.iloc[-1], 2)),
            "total_return_pct": float(round(total_return * 100, 2)),
            "sharpe_ratio": float(round(sharpe, 2)),
            # "equity_curve": equity_curve  # Removed from JSON output for now to avoid serialization error
        }
