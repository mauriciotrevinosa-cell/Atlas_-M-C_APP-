"""
Derivatives Data Aggregator — Phase 1.2
Combines data from multiple derivatives sources into a unified snapshot.
"""
from typing import Dict, Optional
import pandas as pd
from .coinglass import CoinGlassProvider
from .hyperliquid import HyperliquidProvider


class DerivativesAggregator:
    """
    Aggregates derivatives data from CoinGlass + Hyperliquid
    into a single unified market snapshot.

    Usage:
        agg = DerivativesAggregator()
        snapshot = agg.get_snapshot("BTC")
    """

    def __init__(self, coinglass_api_key: Optional[str] = None):
        self._coinglass = CoinGlassProvider(api_key=coinglass_api_key)
        self._hyperliquid = HyperliquidProvider()

    def get_snapshot(self, symbol: str = "BTC") -> Dict:
        """
        Get a full derivatives snapshot for a symbol.

        Returns:
            {
                'symbol': 'BTC',
                'funding': {...},        # From CoinGlass + Hyperliquid
                'open_interest': {...},  # Aggregated OI
                'long_short_ratio': {...},
                'liquidations': {...},   # Recent liquidation summary
            }
        """
        snapshot = {"symbol": symbol, "errors": []}

        # Funding Rates
        try:
            cg_funding = self._coinglass.get_funding_rates(symbol)
            hl_funding = self._hyperliquid.get_funding_rate(symbol)

            avg_funding = float(cg_funding["funding_rate"].mean()) if not cg_funding.empty else None

            snapshot["funding"] = {
                "coinglass_avg": avg_funding,
                "hyperliquid": hl_funding.get("funding_rate"),
                "mark_price": hl_funding.get("mark_price"),
            }
        except Exception as e:
            snapshot["errors"].append(f"Funding: {e}")
            snapshot["funding"] = {}

        # Open Interest
        try:
            oi_df = self._coinglass.get_open_interest(symbol)
            hl_oi = self._hyperliquid.get_funding_rate(symbol)

            snapshot["open_interest"] = {
                "total_usd": float(oi_df["oi_usd"].sum()) if not oi_df.empty else 0,
                "hyperliquid_usd": hl_oi.get("open_interest_usd", 0),
                "by_exchange": oi_df.to_dict("records") if not oi_df.empty else [],
            }
        except Exception as e:
            snapshot["errors"].append(f"OI: {e}")
            snapshot["open_interest"] = {}

        # Long/Short Ratio
        try:
            lsr = self._coinglass.get_long_short_ratio(symbol)
            snapshot["long_short_ratio"] = lsr
        except Exception as e:
            snapshot["errors"].append(f"LSR: {e}")
            snapshot["long_short_ratio"] = {}

        # Liquidations
        try:
            liq = self._coinglass.get_liquidations(symbol)
            if not liq.empty:
                snapshot["liquidations"] = {
                    "total_long_usd": float(liq["long_liq_usd"].sum()),
                    "total_short_usd": float(liq["short_liq_usd"].sum()),
                    "bars": len(liq),
                }
            else:
                snapshot["liquidations"] = {}
        except Exception as e:
            snapshot["errors"].append(f"Liquidations: {e}")
            snapshot["liquidations"] = {}

        return snapshot

    def get_all_funding_rates(self) -> pd.DataFrame:
        """Get all Hyperliquid funding rates (no API key needed)."""
        return self._hyperliquid.get_all_funding_rates()
