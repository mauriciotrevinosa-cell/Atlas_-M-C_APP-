"""
Backtesting Engine
===================
Event-driven backtester with full metrics suite.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.backtest")


@dataclass
class Trade:
    """Represents a completed trade."""
    entry_date: str
    exit_date: str
    side: str          # "long" or "short"
    entry_price: float
    exit_price: float
    size: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.side == "long":
            self.pnl = (self.exit_price - self.entry_price) * self.size
            self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - self.exit_price) * self.size
            self.pnl_pct = (self.entry_price - self.exit_price) / self.entry_price


class BacktestMetrics:
    """Calculate standard performance metrics from trades."""

    @staticmethod
    def calculate(trades: List[Trade], initial_capital: float = 100_000) -> Dict[str, Any]:
        if not trades:
            return {"error": "no_trades"}

        pnls = [t.pnl for t in trades]
        pnl_pcts = [t.pnl_pct for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        # Equity curve
        equity = [initial_capital]
        for p in pnls:
            equity.append(equity[-1] + p)
        equity_series = pd.Series(equity)

        # Drawdown
        peak = equity_series.cummax()
        drawdown = (peak - equity_series) / peak
        max_dd = float(drawdown.max())

        # Returns
        total_return = (equity[-1] - initial_capital) / initial_capital
        n_days = len(trades)  # Approximate
        ann_factor = 252 / max(n_days, 1)

        # Sharpe (annualized)
        if len(pnl_pcts) > 1:
            sharpe = float(np.mean(pnl_pcts) / np.std(pnl_pcts) * np.sqrt(252)) if np.std(pnl_pcts) > 0 else 0
        else:
            sharpe = 0.0

        # Sortino
        downside = [r for r in pnl_pcts if r < 0]
        if downside:
            sortino = float(np.mean(pnl_pcts) / np.std(downside) * np.sqrt(252))
        else:
            sortino = float("inf") if np.mean(pnl_pcts) > 0 else 0.0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Calmar
        calmar = (total_return * ann_factor) / max_dd if max_dd > 0 else 0

        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(len(wins) / len(trades), 3),
            "total_pnl": round(sum(pnls), 2),
            "total_return_pct": round(total_return * 100, 2),
            "avg_trade_pnl": round(float(np.mean(pnls)), 2),
            "avg_win": round(float(np.mean(wins)), 2) if wins else 0,
            "avg_loss": round(float(np.mean(losses)), 2) if losses else 0,
            "largest_win": round(max(pnls), 2),
            "largest_loss": round(min(pnls), 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "calmar_ratio": round(calmar, 3),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "final_equity": round(equity[-1], 2),
        }


class BacktestRunner:
    """
    Event-driven backtester.

    Usage:
        runner = BacktestRunner(strategy_fn=my_strategy, initial_capital=100000)
        results = runner.run(price_data)
    """

    def __init__(
        self,
        strategy_fn: Callable,
        initial_capital: float = 100_000,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005,
    ):
        """
        Args:
            strategy_fn: Function(row, position, context) → "long"/"short"/"close"/None
            initial_capital: Starting capital
            commission_pct: Commission as fraction of trade value
            slippage_pct: Slippage as fraction of price
        """
        self.strategy_fn = strategy_fn
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    def run(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest over OHLCV data.

        Args:
            data: DataFrame with columns: open, high, low, close, volume

        Returns:
            Results dict with trades and metrics
        """
        trades: List[Trade] = []
        position = None  # {"side", "entry_price", "entry_date", "size"}
        capital = self.initial_capital
        context = {"capital": capital, "trades": trades}

        for i, (date, row) in enumerate(data.iterrows()):
            signal = self.strategy_fn(row, position, context)

            if signal in ("long", "short") and position is None:
                # Open position
                slippage = row["close"] * self.slippage_pct
                entry_price = row["close"] + slippage if signal == "long" else row["close"] - slippage
                size = capital * 0.95 / entry_price  # 95% of capital
                commission = abs(size * entry_price * self.commission_pct)
                capital -= commission

                position = {
                    "side": signal,
                    "entry_price": entry_price,
                    "entry_date": str(date),
                    "size": size,
                }

            elif signal == "close" and position is not None:
                # Close position
                slippage = row["close"] * self.slippage_pct
                exit_price = row["close"] - slippage if position["side"] == "long" else row["close"] + slippage
                commission = abs(position["size"] * exit_price * self.commission_pct)

                trade = Trade(
                    entry_date=position["entry_date"],
                    exit_date=str(date),
                    side=position["side"],
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    size=position["size"],
                )
                capital += trade.pnl - commission
                trades.append(trade)
                context["capital"] = capital
                position = None

        # Force close if still in position
        if position is not None and len(data) > 0:
            last = data.iloc[-1]
            trade = Trade(
                entry_date=position["entry_date"],
                exit_date=str(data.index[-1]),
                side=position["side"],
                entry_price=position["entry_price"],
                exit_price=float(last["close"]),
                size=position["size"],
            )
            capital += trade.pnl
            trades.append(trade)

        metrics = BacktestMetrics.calculate(trades, self.initial_capital)

        return {
            "metrics": metrics,
            "trades": [{"entry": t.entry_date, "exit": t.exit_date, "side": t.side,
                         "pnl": round(t.pnl, 2), "pnl_pct": round(t.pnl_pct, 4)} for t in trades],
            "final_capital": round(capital, 2),
            "total_trades": len(trades),
        }
