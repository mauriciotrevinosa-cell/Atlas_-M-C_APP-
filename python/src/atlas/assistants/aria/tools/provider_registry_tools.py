"""
Registry-backed live data tools for ARIA.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from atlas.assistants.aria.tools.base import Tool
from atlas.data_layer import get_provider_registry


def _frame_tail(df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, record in df.tail(limit).iterrows():
        row = {"date": pd.Timestamp(idx).strftime("%Y-%m-%d")}
        for key, value in record.items():
            row[key] = None if pd.isna(value) else float(value)
        rows.append(row)
    return rows


def _article_view(article: Dict[str, Any]) -> Dict[str, Any]:
    source = article.get("source")
    if isinstance(source, dict):
        source = source.get("name")
    return {
        "title": article.get("headline") or article.get("title"),
        "summary": article.get("summary") or article.get("description"),
        "source": source,
        "url": article.get("url"),
        "published_at": article.get("datetime") or article.get("publishedAt"),
    }


class _RegistryBackedTool(Tool):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        category: str,
        registry=None,
    ):
        super().__init__(name=name, description=description, category=category)
        self._registry = registry or get_provider_registry()

    def _error(self, message: str, **extra: Any) -> Dict[str, Any]:
        payload = {
            "success": False,
            "error": message,
            "provider_info": self._registry.get_provider_info(),
        }
        payload.update(extra)
        return payload


class AtlasMarketDataTool(_RegistryBackedTool):
    def __init__(self, registry=None):
        super().__init__(
            name="atlas_market_data",
            description="Get latest quotes or historical OHLCV data through Atlas' provider registry.",
            category="data",
            registry=registry,
        )
        self.add_parameter("symbol", "string", "Ticker symbol such as AAPL, MSFT, SPY, BTC-USD.")
        self.add_parameter(
            "mode",
            "string",
            "Either 'quote' for the latest snapshot or 'historical' for OHLCV bars.",
            required=False,
            default="quote",
        )
        self.add_parameter(
            "start_date",
            "string",
            "Historical start date in YYYY-MM-DD format.",
            required=False,
        )
        self.add_parameter(
            "end_date",
            "string",
            "Historical end date in YYYY-MM-DD format.",
            required=False,
        )
        self.add_parameter(
            "interval",
            "string",
            "Bar interval such as 1d, 1h, 15m, 5m.",
            required=False,
            default="1d",
        )
        self.add_parameter(
            "limit",
            "integer",
            "Maximum number of rows to include in the response payload.",
            required=False,
            default=10,
        )

    def execute(
        self,
        symbol: str,
        mode: str = "quote",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        limit: int = 10,
    ) -> Dict[str, Any]:
        ticker = symbol.strip().upper()
        mode = (mode or "quote").strip().lower()
        limit = max(1, min(int(limit), 50))

        if mode == "quote":
            quote = self._registry.get_quote(ticker)
            if not quote:
                return self._error(f"No quote data available for {ticker}", symbol=ticker, mode=mode)
            return {"success": True, "symbol": ticker, "mode": mode, "data": quote}

        if mode != "historical":
            return self._error(
                "Unsupported mode. Use 'quote' or 'historical'.",
                symbol=ticker,
                mode=mode,
            )

        if not start_date:
            start_date = (date.today() - timedelta(days=90)).isoformat()
        if not end_date:
            end_date = date.today().isoformat()

        frame = self._registry.get_price(ticker, start_date, end_date, interval=interval)
        if frame is None or frame.empty:
            return self._error(
                f"No historical data available for {ticker}",
                symbol=ticker,
                mode=mode,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
            )

        latest = frame.iloc[-1]
        return {
            "success": True,
            "symbol": ticker,
            "mode": mode,
            "start_date": start_date,
            "end_date": end_date,
            "interval": interval,
            "rows": int(len(frame)),
            "latest_close": float(latest["close"]),
            "data": _frame_tail(frame, limit=limit),
        }


class AtlasMacroDataTool(_RegistryBackedTool):
    def __init__(self, registry=None):
        super().__init__(
            name="atlas_macro_data",
            description="Get macroeconomic time series such as GDP, CPI, unemployment, or rates.",
            category="data",
            registry=registry,
        )
        self.add_parameter("series_id", "string", "Series name or code such as GDP, CPI, UNEMPLOYMENT.")
        self.add_parameter("start_date", "string", "Optional start date in YYYY-MM-DD.", required=False)
        self.add_parameter("end_date", "string", "Optional end date in YYYY-MM-DD.", required=False)
        self.add_parameter(
            "limit",
            "integer",
            "Maximum number of rows to include in the response payload.",
            required=False,
            default=10,
        )

    def execute(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        frame = self._registry.get_macro(series_id.strip(), start=start_date, end=end_date)
        if frame is None or frame.empty:
            return self._error(
                f"No macro data available for {series_id}",
                series_id=series_id,
                start_date=start_date,
                end_date=end_date,
            )

        latest = frame.iloc[-1]
        latest_value = latest.iloc[0] if len(latest) else None
        return {
            "success": True,
            "series_id": series_id,
            "rows": int(len(frame)),
            "latest_value": None if pd.isna(latest_value) else float(latest_value),
            "data": _frame_tail(frame, limit=limit),
        }


class AtlasNewsTool(_RegistryBackedTool):
    def __init__(self, registry=None):
        super().__init__(
            name="atlas_news",
            description="Get business or market news from Atlas' provider registry.",
            category="news",
            registry=registry,
        )
        self.add_parameter("query", "string", "Optional company, ticker, or topic to search for.", required=False)
        self.add_parameter(
            "category",
            "string",
            "News category such as general, business, technology, crypto, or forex.",
            required=False,
            default="general",
        )
        self.add_parameter(
            "limit",
            "integer",
            "Maximum number of articles to include in the response payload.",
            required=False,
            default=5,
        )

    def execute(
        self,
        query: Optional[str] = None,
        category: str = "general",
        limit: int = 5,
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 20))
        articles = self._registry.get_news(query=query, category=category)
        if not articles:
            return self._error("No news articles available", query=query, category=category)

        selected = [_article_view(article) for article in articles[:limit]]
        return {
            "success": True,
            "query": query,
            "category": category,
            "count": len(selected),
            "articles": selected,
        }


class AtlasFilingsTool(_RegistryBackedTool):
    def __init__(self, registry=None):
        super().__init__(
            name="atlas_filings",
            description="Get recent SEC filings for a public company.",
            category="filings",
            registry=registry,
        )
        self.add_parameter("ticker", "string", "Public company ticker such as AAPL or MSFT.")
        self.add_parameter(
            "filing_type",
            "string",
            "Filing type such as 10-K, 10-Q, or 8-K.",
            required=False,
            default="10-K",
        )
        self.add_parameter(
            "count",
            "integer",
            "Number of filings to return.",
            required=False,
            default=5,
        )

    def execute(
        self,
        ticker: str,
        filing_type: str = "10-K",
        count: int = 5,
    ) -> Dict[str, Any]:
        ticker = ticker.strip().upper()
        count = max(1, min(int(count), 20))
        filings = self._registry.get_filings(ticker, filing_type=filing_type, count=count)
        if not filings:
            return self._error(
                f"No {filing_type} filings available for {ticker}",
                ticker=ticker,
                filing_type=filing_type,
            )

        return {
            "success": True,
            "ticker": ticker,
            "filing_type": filing_type,
            "count": len(filings),
            "filings": filings[:count],
        }


class AtlasSentimentTool(_RegistryBackedTool):
    def __init__(self, registry=None):
        super().__init__(
            name="atlas_sentiment",
            description="Get sentiment for a symbol or analyze the sentiment of raw text.",
            category="analysis",
            registry=registry,
        )
        self.add_parameter("symbol", "string", "Optional ticker symbol to analyze.", required=False)
        self.add_parameter("text", "string", "Optional raw text to analyze.", required=False)

    def execute(
        self,
        symbol: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Dict[str, Any]:
        ticker = symbol.strip().upper() if symbol else None
        snippet = text.strip() if text else None

        if not ticker and not snippet:
            return self._error("Provide either 'symbol' or 'text' for sentiment analysis.")

        result = self._registry.get_sentiment(symbol=ticker, text=snippet)
        if not result:
            return self._error("No sentiment result available", symbol=ticker, text=snippet)

        return {
            "success": True,
            "symbol": ticker,
            "text": snippet,
            "data": result,
        }
