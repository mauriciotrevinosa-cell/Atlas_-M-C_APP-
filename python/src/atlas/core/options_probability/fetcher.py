"""
Options chain fetching utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd


@dataclass(slots=True)
class OptionsChain:
    symbol: str
    as_of_utc: str
    underlying_price: float
    calls: pd.DataFrame
    puts: pd.DataFrame


class OptionsChainFetcher:
    """Fetches options chains using free data sources (yfinance)."""

    def __init__(self, max_expirations: int = 3, allow_network: bool = True) -> None:
        self.max_expirations = max(1, int(max_expirations))
        self.allow_network = bool(allow_network)

    def fetch(self, symbol: str) -> OptionsChain:
        if not self.allow_network:
            raise RuntimeError("Network fetch disabled for options chain")

        try:
            import yfinance as yf
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("yfinance is required to fetch options data") from exc

        ticker = yf.Ticker(symbol)
        expirations = list(ticker.options or [])[: self.max_expirations]
        if not expirations:
            raise RuntimeError(f"No options expirations found for {symbol}")

        calls_list: list[pd.DataFrame] = []
        puts_list: list[pd.DataFrame] = []
        for expiration in expirations:
            chain = ticker.option_chain(expiration)
            calls = self._normalize_side(chain.calls, side="call", expiration=expiration)
            puts = self._normalize_side(chain.puts, side="put", expiration=expiration)
            if not calls.empty:
                calls_list.append(calls)
            if not puts.empty:
                puts_list.append(puts)

        calls_df = pd.concat(calls_list, ignore_index=True) if calls_list else pd.DataFrame()
        puts_df = pd.concat(puts_list, ignore_index=True) if puts_list else pd.DataFrame()
        if calls_df.empty and puts_df.empty:
            raise RuntimeError(f"No options chain rows available for {symbol}")

        history = ticker.history(period="5d", interval="1d")
        if history is None or history.empty:
            raise RuntimeError(f"Unable to fetch underlying price for {symbol}")
        underlying_price = float(history["Close"].dropna().iloc[-1])

        return OptionsChain(
            symbol=symbol.upper(),
            as_of_utc=datetime.now(timezone.utc).isoformat(),
            underlying_price=underlying_price,
            calls=calls_df,
            puts=puts_df,
        )

    def _normalize_side(self, frame: pd.DataFrame, side: str, expiration: str) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()

        df = frame.copy()
        required = ["strike", "volume", "openInterest", "impliedVolatility"]
        for col in required:
            if col not in df.columns:
                df[col] = 0.0

        for col in ["bid", "ask", "lastPrice"]:
            if col not in df.columns:
                df[col] = pd.NA

        df["expiration"] = pd.to_datetime(expiration, utc=True, errors="coerce")
        df["type"] = side
        for col in ["strike", "volume", "openInterest", "impliedVolatility", "bid", "ask", "lastPrice"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[
            ["strike", "volume", "openInterest", "impliedVolatility", "bid", "ask", "lastPrice", "expiration", "type"]
        ].dropna(subset=["strike", "impliedVolatility"])

