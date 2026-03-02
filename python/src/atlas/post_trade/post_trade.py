"""
Post-Trade Analytics
=====================
Trade journaling, PnL tracking, and performance analytics.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.post_trade")


class TradeJournal:
    """Persistent trade journal with tagging and notes."""

    def __init__(self, journal_path: str = "data/journal/trades.jsonl"):
        self.path = Path(journal_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_trade(
        self,
        trade: Dict[str, Any],
        notes: str = "",
        tags: Optional[List[str]] = None,
        screenshot_path: Optional[str] = None,
    ):
        """Log a completed trade."""
        entry = {
            "logged_at": time.time(),
            "trade": trade,
            "notes": notes,
            "tags": tags or [],
            "screenshot": screenshot_path,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def load_all(self) -> List[Dict]:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def filter_by_tag(self, tag: str) -> List[Dict]:
        return [e for e in self.load_all() if tag in e.get("tags", [])]


class PerformanceAnalytics:
    """Analyze trading performance over time."""

    def daily_pnl(self, trades: List[Dict]) -> pd.Series:
        """Calculate daily PnL from trade list."""
        if not trades:
            return pd.Series(dtype=float)
        records = []
        for t in trades:
            trade_data = t.get("trade", t)
            records.append({
                "date": trade_data.get("exit_date", trade_data.get("exit", "")),
                "pnl": trade_data.get("pnl", 0),
            })
        df = pd.DataFrame(records)
        if df.empty:
            return pd.Series(dtype=float)
        df["date"] = pd.to_datetime(df["date"])
        return df.groupby("date")["pnl"].sum()

    def rolling_sharpe(self, daily_pnl: pd.Series, window: int = 30) -> pd.Series:
        """Rolling Sharpe ratio."""
        rolling_mean = daily_pnl.rolling(window).mean()
        rolling_std = daily_pnl.rolling(window).std()
        return (rolling_mean / rolling_std * np.sqrt(252)).dropna()

    def win_streak_analysis(self, trades: List[Dict]) -> Dict[str, int]:
        """Analyze winning and losing streaks."""
        if not trades:
            return {"max_win_streak": 0, "max_loss_streak": 0, "current_streak": 0}

        pnls = [t.get("trade", t).get("pnl", t.get("pnl", 0)) for t in trades]
        max_win = max_loss = current = 0
        is_winning = None

        for p in pnls:
            if p > 0:
                if is_winning:
                    current += 1
                else:
                    current = 1
                    is_winning = True
                max_win = max(max_win, current)
            elif p < 0:
                if not is_winning and is_winning is not None:
                    current += 1
                else:
                    current = 1
                    is_winning = False
                max_loss = max(max_loss, current)

        return {
            "max_win_streak": max_win,
            "max_loss_streak": max_loss,
            "current_streak": current,
            "current_direction": "win" if is_winning else "loss" if is_winning is not None else "none",
        }

    def summary(self, trades: List[Dict]) -> Dict[str, Any]:
        """Full performance summary."""
        daily = self.daily_pnl(trades)
        streaks = self.win_streak_analysis(trades)

        return {
            "total_trades": len(trades),
            "total_pnl": round(float(daily.sum()), 2) if not daily.empty else 0,
            "best_day": round(float(daily.max()), 2) if not daily.empty else 0,
            "worst_day": round(float(daily.min()), 2) if not daily.empty else 0,
            "avg_daily_pnl": round(float(daily.mean()), 2) if not daily.empty else 0,
            "trading_days": len(daily),
            "streaks": streaks,
        }
