"""
Asset Registry — Multi-Asset Classification
============================================
Classifies tickers by asset class, validates symbols, and supports
cross-asset analysis across Atlas.

Supported asset classes:
  equity     — Blue chip stocks (AAPL, MSFT, NVDA, ...)
  etf        — Broad equity ETFs (SPY, QQQ, VTI, ...)
  bond_etf   — Bond ETFs as bond proxies (TLT, AGG, BND, ...)
  commodity  — Commodity ETFs (GLD, SLV, USO, DBA, ...)
  index      — Market indices (^GSPC, ^IXIC, ^DJI, ...)
  crypto     — Crypto via Yahoo Finance (BTC-USD, ETH-USD, ...)
  forex      — FX pairs via Yahoo Finance (EURUSD=X, ...)
  unknown    — Cannot be classified

Usage:
    from atlas.shared.asset_registry import get_registry

    reg = get_registry()
    reg.classify("SPY")          # → "etf"
    reg.classify("^GSPC")        # → "index"
    reg.validate("AAPL")         # → True
    reg.group_by_class(["AAPL","GLD","TLT","^VIX"])
    # → {"equity": ["AAPL"], "commodity": ["GLD"],
    #    "bond_etf": ["TLT"], "index": ["^VIX"]}

Copyright (c) 2026 M&C. All rights reserved.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AssetInfo:
    """Immutable descriptor for a single asset."""

    ticker: str
    name: str
    asset_class: str        # see module docstring for valid values
    currency: str = "USD"
    exchange: str = ""
    region: str = "US"
    notes: str = ""

    def __post_init__(self) -> None:
        valid = {
            "equity", "etf", "bond_etf", "commodity",
            "index", "crypto", "forex", "unknown",
        }
        if self.asset_class not in valid:
            raise ValueError(
                f"Invalid asset_class '{self.asset_class}'. Must be one of {valid}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

class AssetRegistry:
    """
    Central registry for asset metadata and classification.

    Provides:
      - Pre-loaded universe covering equity, ETF, bond, commodity, index, crypto
      - Runtime registration for custom assets
      - Pattern-based inference for unknown tickers
      - Cross-asset grouping utilities
    """

    # ------------------------------------------------------------------
    # Built-in universe
    # ------------------------------------------------------------------

    _KNOWN: Dict[str, AssetInfo] = {
        # ── Blue chip equities ─────────────────────────────────────────
        "AAPL":  AssetInfo("AAPL",  "Apple Inc.",                "equity"),
        "MSFT":  AssetInfo("MSFT",  "Microsoft Corp.",           "equity"),
        "GOOGL": AssetInfo("GOOGL", "Alphabet Inc. Class A",     "equity"),
        "GOOG":  AssetInfo("GOOG",  "Alphabet Inc. Class C",     "equity"),
        "AMZN":  AssetInfo("AMZN",  "Amazon.com Inc.",           "equity"),
        "NVDA":  AssetInfo("NVDA",  "NVIDIA Corp.",              "equity"),
        "META":  AssetInfo("META",  "Meta Platforms Inc.",       "equity"),
        "TSLA":  AssetInfo("TSLA",  "Tesla Inc.",                "equity"),
        "BRK-B": AssetInfo("BRK-B", "Berkshire Hathaway B",     "equity"),
        "BRK-A": AssetInfo("BRK-A", "Berkshire Hathaway A",     "equity"),
        "JPM":   AssetInfo("JPM",   "JPMorgan Chase & Co.",      "equity"),
        "JNJ":   AssetInfo("JNJ",   "Johnson & Johnson",         "equity"),
        "V":     AssetInfo("V",     "Visa Inc.",                 "equity"),
        "MA":    AssetInfo("MA",    "Mastercard Inc.",           "equity"),
        "PG":    AssetInfo("PG",    "Procter & Gamble Co.",      "equity"),
        "UNH":   AssetInfo("UNH",   "UnitedHealth Group",        "equity"),
        "HD":    AssetInfo("HD",    "Home Depot Inc.",           "equity"),
        "XOM":   AssetInfo("XOM",   "ExxonMobil Corp.",          "equity"),
        "BAC":   AssetInfo("BAC",   "Bank of America Corp.",     "equity"),
        "WMT":   AssetInfo("WMT",   "Walmart Inc.",              "equity"),
        "NFLX":  AssetInfo("NFLX",  "Netflix Inc.",              "equity"),
        "ORCL":  AssetInfo("ORCL",  "Oracle Corp.",              "equity"),
        "CRM":   AssetInfo("CRM",   "Salesforce Inc.",           "equity"),
        "AMD":   AssetInfo("AMD",   "Advanced Micro Devices",    "equity"),
        "INTC":  AssetInfo("INTC",  "Intel Corp.",               "equity"),
        "PYPL":  AssetInfo("PYPL",  "PayPal Holdings Inc.",      "equity"),
        "DIS":   AssetInfo("DIS",   "The Walt Disney Co.",       "equity"),
        "PFE":   AssetInfo("PFE",   "Pfizer Inc.",               "equity"),
        "KO":    AssetInfo("KO",    "Coca-Cola Co.",             "equity"),
        "PEP":   AssetInfo("PEP",   "PepsiCo Inc.",              "equity"),

        # ── Equity ETFs ───────────────────────────────────────────────
        "SPY":   AssetInfo("SPY",  "SPDR S&P 500 ETF Trust",              "etf"),
        "QQQ":   AssetInfo("QQQ",  "Invesco QQQ Trust",                   "etf"),
        "IWM":   AssetInfo("IWM",  "iShares Russell 2000 ETF",            "etf"),
        "VTI":   AssetInfo("VTI",  "Vanguard Total Stock Market ETF",     "etf"),
        "VOO":   AssetInfo("VOO",  "Vanguard S&P 500 ETF",               "etf"),
        "DIA":   AssetInfo("DIA",  "SPDR Dow Jones Industrial Average",   "etf"),
        "IVV":   AssetInfo("IVV",  "iShares Core S&P 500 ETF",           "etf"),
        "VEA":   AssetInfo("VEA",  "Vanguard FTSE Developed Markets ETF", "etf"),
        "VWO":   AssetInfo("VWO",  "Vanguard FTSE Emerging Markets ETF",  "etf"),
        "EFA":   AssetInfo("EFA",  "iShares MSCI EAFE ETF",              "etf"),
        "EEM":   AssetInfo("EEM",  "iShares MSCI Emerging Markets ETF",  "etf"),
        "ARKK":  AssetInfo("ARKK", "ARK Innovation ETF",                 "etf"),
        # Sector ETFs
        "XLK":   AssetInfo("XLK",  "Technology Select Sector SPDR",      "etf"),
        "XLE":   AssetInfo("XLE",  "Energy Select Sector SPDR",          "etf"),
        "XLF":   AssetInfo("XLF",  "Financial Select Sector SPDR",       "etf"),
        "XLV":   AssetInfo("XLV",  "Health Care Select Sector SPDR",     "etf"),
        "XLY":   AssetInfo("XLY",  "Consumer Discretionary SPDR",        "etf"),
        "XLP":   AssetInfo("XLP",  "Consumer Staples SPDR",              "etf"),
        "XLU":   AssetInfo("XLU",  "Utilities Select Sector SPDR",       "etf"),
        "XLI":   AssetInfo("XLI",  "Industrial Select Sector SPDR",      "etf"),
        "XLB":   AssetInfo("XLB",  "Materials Select Sector SPDR",       "etf"),

        # ── Bond ETFs (bond proxies) ──────────────────────────────────
        "TLT":   AssetInfo("TLT",  "iShares 20+ Year Treasury Bond ETF",               "bond_etf"),
        "IEF":   AssetInfo("IEF",  "iShares 7-10 Year Treasury Bond ETF",              "bond_etf"),
        "SHY":   AssetInfo("SHY",  "iShares 1-3 Year Treasury Bond ETF",               "bond_etf"),
        "GOVT":  AssetInfo("GOVT", "iShares US Treasury Bond ETF",                     "bond_etf"),
        "AGG":   AssetInfo("AGG",  "iShares Core US Aggregate Bond ETF",               "bond_etf"),
        "BND":   AssetInfo("BND",  "Vanguard Total Bond Market ETF",                   "bond_etf"),
        "HYG":   AssetInfo("HYG",  "iShares iBoxx USD High Yield Corporate Bond ETF",  "bond_etf"),
        "LQD":   AssetInfo("LQD",  "iShares iBoxx USD Inv Grade Corporate Bond ETF",   "bond_etf"),
        "MUB":   AssetInfo("MUB",  "iShares National Muni Bond ETF",                   "bond_etf"),
        "VCIT":  AssetInfo("VCIT", "Vanguard Intermediate-Term Corporate Bond ETF",    "bond_etf"),
        "VCSH":  AssetInfo("VCSH", "Vanguard Short-Term Corporate Bond ETF",           "bond_etf"),

        # ── Commodity ETFs ────────────────────────────────────────────
        "GLD":   AssetInfo("GLD",  "SPDR Gold Shares",                                "commodity"),
        "IAU":   AssetInfo("IAU",  "iShares Gold Trust",                              "commodity"),
        "SLV":   AssetInfo("SLV",  "iShares Silver Trust",                            "commodity"),
        "USO":   AssetInfo("USO",  "United States Oil Fund",                          "commodity"),
        "BNO":   AssetInfo("BNO",  "United States Brent Oil Fund",                    "commodity"),
        "UNG":   AssetInfo("UNG",  "United States Natural Gas Fund",                  "commodity"),
        "DBA":   AssetInfo("DBA",  "Invesco DB Agriculture Fund",                     "commodity"),
        "PDBC":  AssetInfo("PDBC", "Invesco Optimum Yield Diversified Commodity",     "commodity"),
        "DJP":   AssetInfo("DJP",  "iPath Bloomberg Commodity Total Return ETN",      "commodity"),
        "CPER":  AssetInfo("CPER", "United States Copper Index Fund",                 "commodity"),
        "WEAT":  AssetInfo("WEAT", "Teucrium Wheat Fund",                             "commodity"),
        "CORN":  AssetInfo("CORN", "Teucrium Corn Fund",                              "commodity"),

        # ── Indices (Yahoo Finance format) ────────────────────────────
        "^GSPC":  AssetInfo("^GSPC",  "S&P 500 Index",                    "index"),
        "^IXIC":  AssetInfo("^IXIC",  "NASDAQ Composite Index",           "index"),
        "^DJI":   AssetInfo("^DJI",   "Dow Jones Industrial Average",     "index"),
        "^RUT":   AssetInfo("^RUT",   "Russell 2000 Index",               "index"),
        "^VIX":   AssetInfo("^VIX",   "CBOE Volatility Index",            "index"),
        "^TNX":   AssetInfo("^TNX",   "10-Year Treasury Note Yield",      "index"),
        "^TYX":   AssetInfo("^TYX",   "30-Year Treasury Bond Yield",      "index"),
        "^FVX":   AssetInfo("^FVX",   "5-Year Treasury Note Yield",       "index"),
        "^HSI":   AssetInfo("^HSI",   "Hang Seng Index",                  "index", region="HK"),
        "^FTSE":  AssetInfo("^FTSE",  "FTSE 100 Index",                   "index", region="UK"),
        "^GDAXI": AssetInfo("^GDAXI", "DAX Performance Index",            "index", region="DE"),
        "^N225":  AssetInfo("^N225",  "Nikkei 225 Index",                 "index", region="JP"),

        # ── Crypto (Yahoo Finance) ────────────────────────────────────
        "BTC-USD":  AssetInfo("BTC-USD",  "Bitcoin USD",     "crypto"),
        "ETH-USD":  AssetInfo("ETH-USD",  "Ethereum USD",    "crypto"),
        "SOL-USD":  AssetInfo("SOL-USD",  "Solana USD",      "crypto"),
        "BNB-USD":  AssetInfo("BNB-USD",  "BNB USD",         "crypto"),
        "XRP-USD":  AssetInfo("XRP-USD",  "XRP USD",         "crypto"),
        "ADA-USD":  AssetInfo("ADA-USD",  "Cardano USD",     "crypto"),
        "AVAX-USD": AssetInfo("AVAX-USD", "Avalanche USD",   "crypto"),
        "DOGE-USD": AssetInfo("DOGE-USD", "Dogecoin USD",    "crypto"),

        # ── Forex (Yahoo Finance =X format) ──────────────────────────
        "EURUSD=X": AssetInfo("EURUSD=X", "EUR/USD", "forex"),
        "GBPUSD=X": AssetInfo("GBPUSD=X", "GBP/USD", "forex"),
        "USDJPY=X": AssetInfo("USDJPY=X", "USD/JPY", "forex"),
        "USDCAD=X": AssetInfo("USDCAD=X", "USD/CAD", "forex"),
        "AUDUSD=X": AssetInfo("AUDUSD=X", "AUD/USD", "forex"),
        "USDCHF=X": AssetInfo("USDCHF=X", "USD/CHF", "forex"),
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, extras: Optional[Dict[str, AssetInfo]] = None) -> None:
        """
        Args:
            extras: Optional dict of additional AssetInfo entries to merge
                    on top of the built-in universe.
        """
        self._registry: Dict[str, AssetInfo] = dict(self._KNOWN)
        if extras:
            for ticker, info in extras.items():
                self._registry[ticker.upper()] = info

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, ticker: str) -> Optional[AssetInfo]:
        """Return AssetInfo for ticker, or None if not in registry."""
        return self._registry.get(ticker.upper())

    def classify(self, ticker: str) -> str:
        """
        Return the asset_class string for a ticker.
        Falls back to pattern inference for unknown tickers.
        """
        info = self.get(ticker)
        if info:
            return info.asset_class
        return self._infer_class(ticker)

    def validate(self, ticker: str) -> bool:
        """
        Return True if ticker is known in the registry OR matches
        a recognisable naming pattern (index, crypto, forex).
        Returns False for completely unrecognised symbols.
        """
        t = ticker.upper()
        if t in self._registry:
            return True
        return self._infer_class(t) != "unknown"

    # ------------------------------------------------------------------
    # Registration (extensibility)
    # ------------------------------------------------------------------

    def register(self, info: AssetInfo) -> None:
        """Add or overwrite a single asset entry."""
        self._registry[info.ticker.upper()] = info

    def register_many(self, assets: List[AssetInfo]) -> None:
        """Bulk-register a list of assets."""
        for info in assets:
            self.register(info)

    # ------------------------------------------------------------------
    # Cross-asset analysis helpers
    # ------------------------------------------------------------------

    def filter_by_class(self, asset_class: str) -> List[AssetInfo]:
        """Return all registered assets of a given class."""
        return [a for a in self._registry.values() if a.asset_class == asset_class]

    def group_by_class(self, tickers: List[str]) -> Dict[str, List[str]]:
        """
        Partition a list of tickers into groups by asset class.

        Args:
            tickers: List of ticker strings

        Returns:
            Dict mapping asset_class → [ticker, ...]

        Example:
            {"equity": ["AAPL"], "commodity": ["GLD"], "bond_etf": ["TLT"]}
        """
        groups: Dict[str, List[str]] = {}
        for t in tickers:
            cls = self.classify(t)
            groups.setdefault(cls, []).append(t)
        return groups

    def cross_asset_universe(self) -> Dict[str, List[str]]:
        """
        Return a curated cross-asset universe (one representative per class).
        Useful as a default set for portfolio analysis.
        """
        return {
            "equity":   ["AAPL", "MSFT", "AMZN", "NVDA", "JPM"],
            "etf":      ["SPY", "QQQ", "VTI"],
            "bond_etf": ["TLT", "AGG", "HYG"],
            "commodity": ["GLD", "USO", "SLV"],
            "index":    ["^GSPC", "^VIX", "^TNX"],
            "crypto":   ["BTC-USD", "ETH-USD"],
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, int]:
        """Return count of registered assets per class."""
        return dict(Counter(a.asset_class for a in self._registry.values()))

    def all_tickers(self) -> List[str]:
        """Return sorted list of all registered tickers."""
        return sorted(self._registry.keys())

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in self._registry

    def __repr__(self) -> str:  # pragma: no cover
        return f"AssetRegistry({len(self)} assets, {self.summary()})"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_class(self, ticker: str) -> str:
        """
        Infer asset class from naming conventions when ticker is not in registry.

        Rules (in priority order):
          ^XXX   → index
          XXX-USD / XXX-BTC / XXX-ETH  → crypto
          XXX=X  → forex
          1-4 uppercase letters → equity (heuristic)
          otherwise → unknown
        """
        t = ticker.upper()

        if t.startswith("^"):
            return "index"

        if re.search(r"-(USD|BTC|ETH|USDT|USDC)$", t):
            return "crypto"

        if t.endswith("=X"):
            return "forex"

        # Plain ticker: 1-5 uppercase letters, optionally separated by - or .
        if re.fullmatch(r"[A-Z]{1,5}([.\-][A-Z]{1,2})?", t):
            return "equity"

        return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY: Optional[AssetRegistry] = None


def get_registry() -> AssetRegistry:
    """Return the shared global AssetRegistry instance (lazy-init)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AssetRegistry()
    return _REGISTRY
