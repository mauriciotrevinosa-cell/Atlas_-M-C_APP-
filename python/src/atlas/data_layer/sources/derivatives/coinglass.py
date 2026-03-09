"""
CoinGlass API Connector — Phase 1.2
Derivatives data: Liquidations, Open Interest, Funding Rates, LSR.
Requires: COINGLASS_API_KEY in environment/.env
"""
import os
from typing import Optional, Dict, Any
import pandas as pd

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"


class CoinGlassProvider:
    """
    Wrapper for CoinGlass API (derivatives data).

    Endpoints used:
    - /indicator/funding_rates
    - /indicator/open_interest
    - /indicator/liquidation
    - /indicator/long_short
    """

    def __init__(self, api_key: Optional[str] = None):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not installed. Run: pip install requests")

        self.api_key = api_key or os.environ.get("COINGLASS_API_KEY", "")
        self.headers = {"coinglassSecret": self.api_key, "Content-Type": "application/json"}

    def _get(self, endpoint: str, params: dict = None) -> Dict:
        """Make authenticated GET request."""
        if not self.api_key:
            raise ValueError("COINGLASS_API_KEY not set. See NEEDED_KEYS.md")
        url = f"{COINGLASS_BASE}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params or {}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", False):
            raise ValueError(f"CoinGlass error: {data.get('msg', 'Unknown error')}")
        return data.get("data", {})

    def get_funding_rates(self, symbol: str = "BTC") -> pd.DataFrame:
        """
        Fetch current and historical funding rates.

        Returns:
            DataFrame with [timestamp, exchange, funding_rate]
        """
        raw = self._get("indicator/funding_rates", {"symbol": symbol})
        rows = []
        for exchange_data in raw:
            rows.append({
                "exchange": exchange_data.get("exchangeName", ""),
                "funding_rate": float(exchange_data.get("rate", 0)),
                "predicted_rate": float(exchange_data.get("predictedRate", 0)),
            })
        return pd.DataFrame(rows)

    def get_open_interest(self, symbol: str = "BTC") -> pd.DataFrame:
        """
        Fetch open interest by exchange.

        Returns:
            DataFrame with [exchange, oi_usd, oi_change_pct]
        """
        raw = self._get("indicator/open_interest", {"symbol": symbol})
        rows = []
        for item in raw:
            rows.append({
                "exchange": item.get("exchangeName", ""),
                "oi_usd": float(item.get("openInterest", 0)),
                "oi_change_24h_pct": float(item.get("h24Change", 0)),
            })
        return pd.DataFrame(rows)

    def get_liquidations(self, symbol: str = "BTC", interval: str = "1h") -> pd.DataFrame:
        """
        Fetch liquidation events.

        Returns:
            DataFrame with [timestamp, price, side, size_usd]
        """
        raw = self._get("indicator/liquidation", {"symbol": symbol, "interval": interval})
        rows = []
        for item in raw:
            rows.append({
                "timestamp": pd.to_datetime(item.get("t", 0), unit="ms"),
                "long_liq_usd": float(item.get("longLiquidationUsd", 0)),
                "short_liq_usd": float(item.get("shortLiquidationUsd", 0)),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.set_index("timestamp").sort_index()
        return df

    def get_long_short_ratio(self, symbol: str = "BTC", exchange: str = "Binance") -> dict:
        """
        Fetch current long/short ratio.

        Returns:
            {'long_pct': 55.3, 'short_pct': 44.7, 'exchange': 'Binance'}
        """
        raw = self._get("indicator/long_short", {"symbol": symbol, "exchange": exchange})
        if isinstance(raw, list) and len(raw) > 0:
            item = raw[-1]
        elif isinstance(raw, dict):
            item = raw
        else:
            return {"long_pct": 50.0, "short_pct": 50.0, "exchange": exchange}

        long_pct = float(item.get("longRatio", 0.5)) * 100
        return {
            "long_pct": round(long_pct, 1),
            "short_pct": round(100 - long_pct, 1),
            "exchange": exchange,
            "symbol": symbol,
        }
