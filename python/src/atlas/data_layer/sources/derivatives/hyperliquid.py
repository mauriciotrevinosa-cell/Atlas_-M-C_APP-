"""
Hyperliquid API Connector — Phase 1.2
Fetches perpetual futures data directly from Hyperliquid DEX.
No API key required — public endpoints.
"""
from typing import Dict, Any, Optional
import pandas as pd

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

HYPERLIQUID_BASE = "https://api.hyperliquid.xyz/info"


class HyperliquidProvider:
    """
    Wrapper for Hyperliquid public API.
    Provides: funding rates, open interest, mark price, liquidations.
    """

    def __init__(self):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not installed. Run: pip install requests")

    def _post(self, payload: dict) -> Any:
        """Make POST request to Hyperliquid info endpoint."""
        resp = requests.post(
            HYPERLIQUID_BASE,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_meta_and_contexts(self) -> list:
        """Fetch metadata for all perpetual markets."""
        return self._post({"type": "metaAndAssetCtxs"})

    def get_funding_rate(self, symbol: str) -> Dict:
        """
        Get current funding rate for a Hyperliquid perpetual.

        Args:
            symbol: e.g. 'BTC', 'ETH', 'SOL'

        Returns:
            {'symbol': ..., 'funding_rate': ..., 'open_interest': ..., 'mark_price': ...}
        """
        data = self._post({"type": "metaAndAssetCtxs"})

        if not data or len(data) < 2:
            return {"error": "No data from Hyperliquid"}

        meta = data[0].get("universe", [])
        contexts = data[1]

        for i, asset in enumerate(meta):
            if asset.get("name", "").upper() == symbol.upper():
                ctx = contexts[i] if i < len(contexts) else {}
                return {
                    "symbol": symbol,
                    "funding_rate": float(ctx.get("funding", 0)),
                    "open_interest_usd": float(ctx.get("openInterest", 0)),
                    "mark_price": float(ctx.get("markPx", 0)),
                    "oracle_price": float(ctx.get("oraclePx", 0)),
                }

        return {"error": f"Symbol '{symbol}' not found on Hyperliquid"}

    def get_all_funding_rates(self) -> pd.DataFrame:
        """
        Get funding rates for all Hyperliquid perpetuals.

        Returns:
            DataFrame with [symbol, funding_rate, open_interest_usd, mark_price]
        """
        data = self._post({"type": "metaAndAssetCtxs"})

        if not data or len(data) < 2:
            return pd.DataFrame()

        meta = data[0].get("universe", [])
        contexts = data[1]

        rows = []
        for i, asset in enumerate(meta):
            ctx = contexts[i] if i < len(contexts) else {}
            rows.append({
                "symbol": asset.get("name", ""),
                "funding_rate": float(ctx.get("funding", 0)),
                "open_interest_usd": float(ctx.get("openInterest", 0)),
                "mark_price": float(ctx.get("markPx", 0)),
            })

        return pd.DataFrame(rows)
