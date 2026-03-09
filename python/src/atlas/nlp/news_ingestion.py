"""
News Ingestion Pipeline
========================
Fetches financial news from free/public sources and converts them
into SentimentSignal objects for the Atlas NLP pipeline.

Sources:
  - Yahoo Finance RSS feeds (free, no API key)
  - Finviz news scraper (free)
  - Alpha Vantage News API (requires key — graceful fallback)
  - Custom RSS/atom feed parser

All fetching is non-blocking with configurable timeout and caching.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

from .sentiment_engine import SentimentEngine, SentimentSignal

logger = logging.getLogger("atlas.nlp.news_ingestion")


# ── RSS Feed Config ────────────────────────────────────────────────────────────

YAHOO_FINANCE_RSS = "https://finance.yahoo.com/rss/topstories"
MARKETWATCH_RSS   = "https://feeds.marketwatch.com/marketwatch/topstories/"
CNBC_RSS          = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
REUTERS_MARKETS   = "https://feeds.reuters.com/reuters/businessNews"

TICKER_NEWS_TEMPLATE = "https://finance.yahoo.com/rss/headline?s={ticker}"

# Public APIs (no key needed)
FREE_RSS_FEEDS: List[str] = [
    YAHOO_FINANCE_RSS,
    MARKETWATCH_RSS,
]


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class NewsArticle:
    """Raw news article before sentiment analysis."""
    title: str
    description: str = ""
    url: str = ""
    published: str = ""
    source: str = ""
    ticker: str = ""

    def full_text(self) -> str:
        return f"{self.title}. {self.description}".strip()

    def article_id(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()[:10]


@dataclass
class NewsIngestResult:
    """Result of a news ingestion run."""
    articles: List[NewsArticle] = field(default_factory=list)
    signals: List[SentimentSignal] = field(default_factory=list)
    n_fetched: int = 0
    n_analysed: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "n_fetched":  self.n_fetched,
            "n_analysed": self.n_analysed,
            "errors":     self.errors,
            "signals":    [s.to_dict() for s in self.signals],
            "timestamp":  self.timestamp,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  RSS Parser
# ══════════════════════════════════════════════════════════════════════════════

class RSSParser:
    """Parse RSS/Atom feeds into NewsArticle objects."""

    _NAMESPACES = {
        "media": "http://search.yahoo.com/mrss/",
        "dc":    "http://purl.org/dc/elements/1.1/",
    }

    def fetch(self, url: str, timeout: int = 8) -> List[NewsArticle]:
        """Fetch and parse an RSS feed."""
        articles = []
        try:
            req = Request(url, headers={"User-Agent": "AtlasBot/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            articles = self._parse(raw, url)
            logger.debug("RSS [%s]: fetched %d articles", url[:60], len(articles))
        except URLError as exc:
            logger.warning("RSS fetch failed [%s]: %s", url[:60], exc)
        except ET.ParseError as exc:
            logger.warning("RSS parse error [%s]: %s", url[:60], exc)
        return articles

    def _parse(self, xml_text: str, source_url: str) -> List[NewsArticle]:
        articles = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return articles

        # RSS 2.0
        for item in root.iter("item"):
            title  = self._text(item, "title")
            desc   = self._text(item, "description")
            link   = self._text(item, "link")
            pubdate = self._text(item, "pubDate")
            if title:
                articles.append(NewsArticle(
                    title=title[:500],
                    description=self._clean_html(desc)[:1000],
                    url=link,
                    published=pubdate,
                    source=source_url,
                ))

        # Atom
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title  = self._text(entry, "{http://www.w3.org/2005/Atom}title")
            summ   = self._text(entry, "{http://www.w3.org/2005/Atom}summary")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link   = link_el.get("href", "") if link_el is not None else ""
            if title:
                articles.append(NewsArticle(
                    title=title[:500],
                    description=self._clean_html(summ)[:1000],
                    url=link,
                    source=source_url,
                ))

        return articles

    @staticmethod
    def _text(el: ET.Element, tag: str) -> str:
        child = el.find(tag)
        if child is None:
            return ""
        return (child.text or "").strip()

    @staticmethod
    def _clean_html(text: str) -> str:
        import re
        return re.sub(r"<[^>]+>", " ", text).strip()


# ══════════════════════════════════════════════════════════════════════════════
#  In-Memory Cache
# ══════════════════════════════════════════════════════════════════════════════

class _NewsCache:
    """Simple TTL cache to avoid re-fetching within the same session."""

    def __init__(self, ttl_seconds: int = 300):
        self._data: Dict[str, tuple] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[List[NewsArticle]]:
        if key in self._data:
            articles, ts = self._data[key]
            if time.time() - ts < self._ttl:
                return articles
            del self._data[key]
        return None

    def set(self, key: str, articles: List[NewsArticle]) -> None:
        self._data[key] = (articles, time.time())


# ══════════════════════════════════════════════════════════════════════════════
#  NewsIngestion Pipeline
# ══════════════════════════════════════════════════════════════════════════════

class NewsIngestion:
    """
    Fetches news from multiple RSS sources, deduplicates, and runs
    sentiment analysis via SentimentEngine.

    Usage:
        ingestion = NewsIngestion()

        # General market news
        result = ingestion.fetch_market_news()

        # Ticker-specific news
        result = ingestion.fetch_ticker_news("AAPL")

        # Access signals
        for sig in result.signals:
            print(sig.to_dict())
    """

    def __init__(
        self,
        feeds: Optional[List[str]] = None,
        cache_ttl: int = 300,
        max_articles: int = 50,
    ):
        self.feeds       = feeds or FREE_RSS_FEEDS
        self.rss_parser  = RSSParser()
        self.nlp_engine  = SentimentEngine()
        self._cache      = _NewsCache(ttl_seconds=cache_ttl)
        self.max_articles = max_articles
        self._seen_ids: set = set()
        logger.info("NewsIngestion initialised with %d feeds", len(self.feeds))

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_market_news(self) -> NewsIngestResult:
        """Fetch general market news from all configured feeds."""
        result = NewsIngestResult()
        all_articles: List[NewsArticle] = []

        for feed_url in self.feeds:
            cached = self._cache.get(feed_url)
            if cached is not None:
                all_articles.extend(cached)
            else:
                articles = self.rss_parser.fetch(feed_url)
                self._cache.set(feed_url, articles)
                all_articles.extend(articles)

        result.articles  = self._deduplicate(all_articles)[:self.max_articles]
        result.n_fetched = len(result.articles)
        result = self._analyse(result, source="news")
        return result

    def fetch_ticker_news(self, ticker: str) -> NewsIngestResult:
        """Fetch news specific to a ticker symbol."""
        result = NewsIngestResult()
        url    = TICKER_NEWS_TEMPLATE.format(ticker=ticker.upper())

        cached = self._cache.get(url)
        if cached is not None:
            articles = cached
        else:
            articles = self.rss_parser.fetch(url)
            self._cache.set(url, articles)

        for a in articles:
            a.ticker = ticker.upper()

        result.articles  = self._deduplicate(articles)[:self.max_articles]
        result.n_fetched = len(result.articles)
        result = self._analyse(result, source="news", ticker_context=ticker)
        return result

    def ingest_custom(
        self,
        texts: List[str],
        source: str = "news",
        ticker: str = "",
    ) -> NewsIngestResult:
        """
        Ingest and analyse pre-fetched text items directly (e.g. from API).

        Parameters
        ----------
        texts  : List of raw text strings
        source : 'news' | 'fed' | 'social' | 'transcript'
        ticker : Optional associated ticker

        Returns NewsIngestResult.
        """
        result = NewsIngestResult()
        articles = [
            NewsArticle(title=t[:500], ticker=ticker.upper())
            for t in texts if t.strip()
        ]
        result.articles  = articles
        result.n_fetched = len(articles)
        result = self._analyse(result, source=source, ticker_context=ticker or None)
        return result

    # ── Internal ──────────────────────────────────────────────────────────────

    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove articles seen before or with duplicate URLs."""
        seen = set()
        unique = []
        for a in articles:
            aid = a.article_id()
            if aid not in self._seen_ids and aid not in seen:
                seen.add(aid)
                unique.append(a)
        self._seen_ids.update(seen)
        return unique

    def _analyse(
        self,
        result: NewsIngestResult,
        source: str,
        ticker_context: Optional[str] = None,
    ) -> NewsIngestResult:
        """Run NLP sentiment analysis on all articles."""
        signals = []
        for article in result.articles:
            try:
                sig = self.nlp_engine.analyse(
                    article.full_text(),
                    source=source,
                    ticker_context=ticker_context or article.ticker or None,
                )
                signals.append(sig)
            except Exception as exc:
                logger.warning("Sentiment analysis failed for '%s…': %s", article.title[:40], exc)
                result.errors.append(str(exc))

        result.signals    = signals
        result.n_analysed = len(signals)
        return result
