"""
Get Data Tool for ARIA

Provides market data through multiple providers with automatic
offline fallback via the Atlas DataRouter.

Copyright (c) 2026 M&C. All rights reserved.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria.tools.base import Tool
from typing import Any, Dict, Optional
import pandas as pd


class GetDataTool(Tool):
    """
    Tool for getting market data.

    Supports:
    - Historical data (Yahoo Finance with Parquet cache fallback)
    - Real-time quotes (Yahoo Finance delayed, ~15 min)

    Uses atlas.data_router.DataRouter with allow_network=True so that
    live data is fetched and written to cache; if the network is down
    or yfinance fails, the stale cache is returned automatically.

    Examples:
        >>> tool = GetDataTool()
        >>>
        >>> # Historical data
        >>> data = tool.execute(
        >>>     symbol="AAPL",
        >>>     mode="historical",
        >>>     start_date="2024-01-01",
        >>>     end_date="2024-12-31"
        >>> )
        >>>
        >>> # Latest quote
        >>> quote = tool.execute(
        >>>     symbol="AAPL",
        >>>     mode="realtime"
        >>> )
    """

    def __init__(self):
        super().__init__(
            name="get_data",
            description="Get market data (historical or real-time) for stocks",
            category="data"
        )

        # Add parameters
        self.add_parameter(
            "symbol",
            "string",
            "Ticker symbol (e.g., AAPL, TSLA, SPY)"
        )

        self.add_parameter(
            "mode",
            "string",
            "Data mode: 'historical' or 'realtime'",
            required=True
        )

        self.add_parameter(
            "start_date",
            "string",
            "Start date for historical data (YYYY-MM-DD)",
            required=False
        )

        self.add_parameter(
            "end_date",
            "string",
            "End date for historical data (YYYY-MM-DD)",
            required=False
        )

        self.add_parameter(
            "timeframe",
            "string",
            "Timeframe (e.g. '1y', 'ytd', 'max'). Overrides start/end date.",
            required=False
        )

        self.add_parameter(
            "interval",
            "string",
            "Data interval: 1d, 1h, 1m (default: 1d)",
            required=False,
            default="1d"
        )

        # Initialize DataRouter (online by default; falls back to cache on failure)
        from atlas.data_router import DataRouter
        self._router = DataRouter(allow_network=True)
        print("✅ DataRouter initialized for ARIA tool")
    
    def execute(
        self,
        symbol: str,
        mode: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeframe: Optional[str] = None,
        interval: str = "1d"
    ) -> Any:
        """
        Execute the get_data tool
        """
        # Validate parameters
        self.validate_parameters(
            symbol=symbol,
            mode=mode
        )
        
        symbol = symbol.upper()
        
        try:
            if mode == "historical":
                return self._get_historical(symbol, start_date, end_date, timeframe, interval)
            elif mode == "realtime":
                return self._get_realtime(symbol)
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'historical' or 'realtime'")
                
        except Exception as e:
            return {
                "error": str(e),
                "symbol": symbol,
                "mode": mode
            }
    
    def _get_historical(
        self,
        symbol: str,
        start_date: Optional[str],
        end_date: Optional[str],
        timeframe: Optional[str],
        interval: str
    ) -> pd.DataFrame:
        """Get historical data via DataRouter (yfinance + cache fallback)."""
        from datetime import date, timedelta

        # Resolve timeframe → start/end dates
        if not start_date:
            if not timeframe or timeframe == "1y":
                start_date = (date.today() - timedelta(days=365)).isoformat()
            elif timeframe == "6mo":
                start_date = (date.today() - timedelta(days=183)).isoformat()
            elif timeframe == "3mo":
                start_date = (date.today() - timedelta(days=91)).isoformat()
            elif timeframe == "ytd":
                start_date = date(date.today().year, 1, 1).isoformat()
            elif timeframe == "max":
                start_date = "1990-01-01"
            else:
                # Try parsing e.g. "2y", "5y"
                try:
                    years = int(timeframe.rstrip("y"))
                    start_date = (date.today() - timedelta(days=365 * years)).isoformat()
                except Exception:
                    start_date = (date.today() - timedelta(days=365)).isoformat()

        if not end_date:
            end_date = date.today().isoformat()

        print(f"📊 Fetching historical data for {symbol} ({start_date} → {end_date} @ {interval})")

        data = self._router.get(
            ticker=symbol,
            start=start_date,
            end=end_date,
            interval=interval,
        )

        print(f"✅ Got {len(data)} bars")
        return data

    def _get_realtime(self, symbol: str) -> Dict:
        """Get latest delayed quote via DataRouter."""
        print(f"🔴 Fetching real-time quote for {symbol}")
        quote = self._router.get_quote(symbol)
        price = quote.get("price")
        print(f"✅ Quote received: {price}")
        return quote


# Test if executed directly
if __name__ == "__main__":
    print("🧪 Testing GetDataTool...\n")
    
    tool = GetDataTool()
    
    # Test 1: Historical data
    print("\nTEST 1: Historical data")
    print("-" * 60)
    data = tool.execute(
        symbol="AAPL",
        mode="historical",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    print(f"Got {len(data)} rows")
    print(data.head())
    
    # Test 2: Real-time quote
    print("\nTEST 2: Real-time quote")
    print("-" * 60)
    quote = tool.execute(
        symbol="AAPL",
        mode="realtime"
    )
    print(quote)
    
    print("\n✅ GetDataTool working!")