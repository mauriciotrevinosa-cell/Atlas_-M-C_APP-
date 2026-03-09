"""
Scenario Session Manager
========================

Manages interactive 'Time Machine' sessions for the Desktop App.
Allows stepping through historical data with full state inspection.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger("atlas.scenario")


def _generate_synthetic_history(ticker: str, n: int = 1260) -> pd.DataFrame:
    """
    Build deterministic OHLCV history for offline/fallback scenario sessions.
    """
    seed = abs(hash(ticker.upper())) % (2**31)
    rng = np.random.default_rng(seed)

    mu = 0.00025 + (seed % 17) * 0.00001
    sigma = 0.012 + (seed % 11) * 0.001
    start_price = 80.0 + (seed % 420)

    closes = [start_price]
    for _ in range(max(1, n - 1)):
        step = rng.normal(mu - 0.5 * sigma**2, sigma)
        closes.append(closes[-1] * np.exp(step))

    closes = np.array(closes, dtype=float)
    spread = rng.uniform(0.002, 0.015, size=n)
    highs = closes * (1 + spread)
    lows = closes * (1 - spread)
    opens = np.concatenate([[closes[0]], closes[:-1]]) * rng.uniform(0.997, 1.003, size=n)
    opens = np.clip(opens, lows, highs)
    vols = rng.lognormal(mean=12.0, sigma=0.8, size=n).astype(int)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")

    frame = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": vols,
        },
        index=dates,
    )
    frame["date"] = frame.index
    return frame


def _load_ticker_history(ticker: str, period: str = "5y") -> tuple[pd.DataFrame, bool]:
    """
    Fetch ticker history with Yahoo first; fallback to deterministic synthetic OHLCV.
    """
    period_bars = {
        "1mo": 21,
        "3mo": 63,
        "6mo": 126,
        "1y": 252,
        "2y": 504,
        "5y": 1260,
    }
    n_bars = period_bars.get(period, 1260)

    try:
        import yfinance as yf

        data = yf.Ticker(ticker.upper()).history(period=period, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if not data.empty:
            data = data[["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
            data.columns = [c.lower() for c in data.columns]
            data["date"] = data.index
            return data, False
    except Exception:
        pass

    return _generate_synthetic_history(ticker, n=n_bars), True

@dataclass
class ScenarioState:
    """Snapshot of the simulation state at a specific step."""
    date: str
    price: float
    capital: float
    holdings: float
    portfolio_value: float
    indicators: Dict[str, float]
    decision: str  # "buy", "sell", "hold"
    reasoning: List[str]  # Log of why the decision was made
    positions: Dict[str, Dict[str, Any]] = field(default_factory=dict) # NEW: Full portfolio state

class ScenarioSession:
    """
    Interactive backtest session.
    
    Usage:
        session = ScenarioSession(ticker="SPY", start_date="2000-01-01", initial_capital=10000)
        state = session.next_step()
    """
    
    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000.0, ticker: str = "SPY"):
        self.data = data
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # Portfolio: { "SPY": {"qty": 10, "avg_price": 300.0, "last_price": 300.0} }
        self.positions: Dict[str, Dict[str, float]] = {} 
        
        self.current_step = 0
        self.current_date_str = ""
        self.history: List[ScenarioState] = []
        self.logs: List[str] = []
        
        # Initialize News Engine
        self.news_engine = NewsEngine(ticker)
        
        # Initialize AutoTrader
        self._init_auto_trader()
        
        # Pre-calculate indicators (simplified for now, ideally use Features Registry)
        self._prepare_data()

    def _prepare_data(self):
        """Calculate indicators for the entire dataset upfront."""
        # Simple Moving Averages
        self.data['SMA_50'] = self.data['close'].rolling(window=50).mean()
        self.data['SMA_200'] = self.data['close'].rolling(window=200).mean()
        
        # RSI
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # Fill NaNs
        self.data.fillna(0, inplace=True)

    def _init_auto_trader(self):
        """Initialize the AutoTrader with default strategies."""
        try:
            from atlas.auto_trader.auto_trader import AutoTrader, TradingMode, Decision
            
            self.trader = AutoTrader(mode=TradingMode.ADVISORY)
            
            # 1. Register Rule-Based Source (The "Old" Logic)
            def rule_strategy(symbol, features, state):
                price = features.get('close', 0)
                sma200 = features.get('SMA_200', 0)
                rsi = features.get('RSI', 50)
                
                action = "hold"
                confidence = 0.5
                reason = "Neutral"
                
                if price > sma200 and rsi < 40:
                    action = "buy"
                    confidence = 0.8
                    reason = "Trend Follow + Oversold"
                elif (price < sma200 or rsi > 70) and state.get('holdings', 0) > 0:
                    action = "sell"
                    confidence = 0.7
                    reason = "Trend Break or Overbought"
                    
                return Decision("rules_engine", action, symbol, confidence, reason)
                
            self.trader.register_source("technical_rules", rule_strategy, weight=0.4)
            
            # 2. Register Mock ML Source (Placeholder until trained)
            def ml_strategy(symbol, features, state):
                # In a real scenario, this would call self.ml_engine.predict(features)
                # For now, we simulate a "cautious" AI
                return Decision("ml_forest", "hold", symbol, 0.3, "Model not trained - observing", {})
                
            self.trader.register_source("ml_core", ml_strategy, weight=0.1)
            
            logger.info("AutoTrader initialized for Scenario Simulation")
            
        except ImportError:
            logger.error("Could not import AutoTrader - falling back to legacy mode")
            self.trader = None

    def switch_ticker(self, new_ticker: str):
        """
        Switch the simulation to a new ticker, maintaining date and capital.
        """
        logger.info(f"Switching simulation to {new_ticker}...")

        # 1. Fetch new data (real first, deterministic fallback)
        new_data, is_synthetic = _load_ticker_history(new_ticker, period="5y")
        if new_data.empty:
            logger.error(f"No data found for {new_ticker}")
            return False
        if is_synthetic:
            logger.warning("Using synthetic fallback data for %s", new_ticker)

        # 3. Find matching index for current_date
        # We try to find the closest date
        try:
            # Ensure index is datetime
            if not isinstance(new_data.index, pd.DatetimeIndex):
                new_data.index = pd.to_datetime(new_data.index)
            
            if not self.current_date_str:
                self.current_date_str = str(self.data.index[self.current_step]).split(" ")[0]

            target_date = pd.to_datetime(self.current_date_str)
            
            # Find closest date (using get_loc with 'nearest' or similar logic)
            # Simpler: filter dates >= target and take first
            future_dates = new_data.index[new_data.index >= target_date]
            
            if len(future_dates) == 0:
                logger.warning(f"No data for {new_ticker} after {self.current_date_str}")
                # Fallback: Start from beginning if we are past the end? 
                # Or just refuse.
                return False
                
            start_date = future_dates[0]
            start_idx = new_data.index.get_loc(start_date)
            
            self.data = new_data
            self.ticker = new_ticker
            self.current_step = start_idx
            self.news_engine = NewsEngine(new_ticker) # Reset news for new ticker
            self._prepare_data() # Recalc indicators
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching ticker: {e}")
            return False

    def next_step(self) -> Optional[ScenarioState]:
        """Advance the simulation by one day."""
        if self.current_step >= len(self.data):
            return None

        row = self.data.iloc[self.current_step]
        # Robust date handling
        if isinstance(self.data.index, pd.DatetimeIndex):
            date_obj = self.data.index[self.current_step]
            self.current_date_str = str(date_obj).split(" ")[0]
        else:
            self.current_date_str = str(getattr(row, 'date', 'Unknown'))
            
        price = float(row['close'])
        
        # Update "last_price" for current ticker in portfolio
        if self.ticker in self.positions:
            self.positions[self.ticker]['last_price'] = price

        # Get News
        news_items = self.news_engine.get_news(self.current_date_str)
        
        # Prepare Features for AutoTrader
        features = {
            "close": price,
            "SMA_50": float(row.get('SMA_50', 0)),
            "SMA_200": float(row.get('SMA_200', 0)),
            "RSI": float(row.get('RSI', 50)),
            "volume": float(row.get('volume', 0))
        }
        
        # Calculate current holdings of ACTIVE ticker for state
        current_holdings = self.positions.get(self.ticker, {}).get('qty', 0)
        
        portfolio_state = {
            "capital": self.capital,
            "holdings": current_holdings,
            "positions": self.positions
        }

        # --- AI Decision Logic ---
        decision = "hold"
        reasoning = []
        
        if hasattr(self, 'trader') and self.trader:
            # Use AutoTrader
            result = self.trader.decide(self.ticker, features, portfolio_state)
            consensus = result.get('consensus', {})
            
            decision = consensus.get('action', 'hold')
            conf = consensus.get('confidence', 0)
            reason = consensus.get('reasoning', '')
            
            # Format Reasoning for UI
            if decision != "hold":
                icon = "🚀" if decision == "buy" else "🛑"
                reasoning.append(f"{icon} {decision.upper()} Signal (Conf: {conf:.0%})")
                reasoning.append(f"Analyzed by: {reason}")
            else:
                reasoning.append(f"⚖️ Hold. (Conf: {conf:.0%})")
                
        else:
            # Fallback Legacy Logic
            decision, rules_reasoning = self._make_decision(row)
            reasoning.extend(rules_reasoning)
        
        # Add news to reasoning log if important
        if news_items:
            reasoning.append(f"📰 NEWS: {news_items[0]['title']}")
        
        # Execute Decision on GLOBAL Portfolio
        if decision == "buy" and self.capital > price:
            # Buy max possible (simple logic)
            shares_to_buy = int((self.capital * 0.95) // price)
            if shares_to_buy > 0:
                cost = shares_to_buy * price
                self.capital -= cost
                
                if self.ticker not in self.positions:
                    self.positions[self.ticker] = {"qty": 0, "avg_price": 0.0, "last_price": price}
                
                pos = self.positions[self.ticker]
                total_cost = (pos['qty'] * pos['avg_price']) + cost
                pos['qty'] += shares_to_buy
                pos['avg_price'] = total_cost / pos['qty']
                pos['last_price'] = price
                
                reasoning.append(f"Executed BUY: {shares_to_buy} {self.ticker} @ ${price:.2f}")

        elif decision == "sell":
            qty = self.positions.get(self.ticker, {}).get('qty', 0)
            if qty > 0:
                revenue = qty * price
                self.capital += revenue
                del self.positions[self.ticker] # Close position
                reasoning.append(f"Executed SELL: {qty} {self.ticker} @ ${price:.2f}")
            
        # Calculate Total Portfolio Value
        equity_value = sum(p['qty'] * p['last_price'] for p in self.positions.values())
        total_value = self.capital + equity_value
        
        indicators = {
            "SMA_50": round(float(row.get('SMA_50', 0)), 2),
            "SMA_200": round(float(row.get('SMA_200', 0)), 2),
            "RSI": round(float(row.get('RSI', 0)), 2)
        }
        
        state = ScenarioState(
            date=self.current_date_str,
            price=price,
            capital=round(self.capital, 2),
            holdings=self.positions.get(self.ticker, {}).get('qty', 0),
            portfolio_value=round(total_value, 2),
            indicators=indicators,
            decision=decision,
            reasoning=reasoning,
            positions=self.positions # Pass full portfolio
        )
        
        self.history.append(state)
        self.current_step += 1
        return state

    def _make_decision(self, row: pd.Series) -> (str, List[str]):
        """Legacy Logic (Fallback)."""
        # ... kept for safety ...
        return "hold", ["Legacy logic active"]

    def get_full_history(self) -> List[Dict]:
        return [vars(s) for s in self.history]


class NewsEngine:
    """
    Simulates a news feed for the scenario.
    Fetches real historical news if available (via yfinance/Google) or generates context-aware synthetic news.
    """
    def __init__(self, ticker):
        self.ticker = ticker
        self.events = self._load_events()

    def _load_events(self):
        # Basic events for SPY/BTC to demonstrate functionality
        return {
            "2020-02-20": ["Market jitters increase as virus concerns spread globally.", "Goldman Sachs warns of potential correction."],
            "2020-03-09": ["BLACK MONDAY: Market crashes amidst oil price war and pandemic fears.", "Trading halted as circuit breakers trigger."],
            "2020-03-12": ["Fed injects $1.5 Trillion into repo market.", "Selling intensifies across all asset classes."],
            "2020-03-23": ["Fed announces unlimited QE to support economy.", "Market creates a potential bottom structure."],
            "2020-11-09": ["Vaccine breakthrough announced by Pfizer.", "Markets rally on reopening hopes."],
            "2021-01-04": ["New year begins with high volatility.", "Tech sector leads market gains."]
        }

    def get_news(self, date_str):
        """Get news for a specific date."""
        if date_str in self.events:
            return [{"title": title, "source": "Financial Wire", "sentiment": "Mixed"} for title in self.events[date_str]]
        return []
