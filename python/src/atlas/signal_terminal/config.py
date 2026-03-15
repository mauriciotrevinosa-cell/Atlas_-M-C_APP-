"""
Signal Terminal — Configuration
"""
import os
from pathlib import Path

# ── Storage ────────────────────────────────────────────────────────────────
DATA_DIR  = Path(os.getenv("ATLAS_DATA_DIR", "data"))
DB_PATH   = DATA_DIR / "signal_terminal.db"

# ── Scheduler ──────────────────────────────────────────────────────────────
DEFAULT_REFRESH_INTERVAL = int(os.getenv("ST_REFRESH_INTERVAL", "300"))  # seconds
MAX_SIGNALS_PER_RUN      = int(os.getenv("ST_MAX_SIGNALS", "100"))

# ── Deduplication ──────────────────────────────────────────────────────────
DEDUP_WINDOW_HOURS = 48      # ignore signals with same hash seen within N hours

# ── Scoring ────────────────────────────────────────────────────────────────
RELEVANCE_DECAY_HOURS = 24   # signals older than this get lower relevance
HIGH_RELEVANCE_THRESHOLD = 0.7
WHALE_SIZE_THRESHOLDS = {     # minimum $ value to qualify as whale event
    "micro":  1_000_000,
    "mid":   10_000_000,
    "large": 50_000_000,
}

# ── Default RSS sources ────────────────────────────────────────────────────
DEFAULT_RSS_SOURCES = [
    {
        "id": "yahoo_finance_news",
        "name": "Yahoo Finance — Top News",
        "url": "https://finance.yahoo.com/news/rssindex",
        "refresh_interval": 300,
    },
    {
        "id": "marketwatch_top",
        "name": "MarketWatch — Top Stories",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "refresh_interval": 300,
    },
    {
        "id": "coindesk",
        "name": "CoinDesk — Latest",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "refresh_interval": 600,
    },
    {
        "id": "seeking_alpha_market",
        "name": "Seeking Alpha — Market News",
        "url": "https://seekingalpha.com/market_currents.xml",
        "refresh_interval": 600,
    },
]

# ── Default Reddit sources ─────────────────────────────────────────────────
DEFAULT_REDDIT_SOURCES = [
    {
        "id": "reddit_stocks",
        "name": "Reddit r/stocks",
        "subreddit": "stocks",
        "sort": "new",
        "limit": 25,
        "refresh_interval": 600,
    },
    {
        "id": "reddit_wsb",
        "name": "Reddit r/wallstreetbets",
        "subreddit": "wallstreetbets",
        "sort": "hot",
        "limit": 25,
        "refresh_interval": 900,
    },
    {
        "id": "reddit_investing",
        "name": "Reddit r/investing",
        "subreddit": "investing",
        "sort": "new",
        "limit": 20,
        "refresh_interval": 600,
    },
    {
        "id": "reddit_crypto",
        "name": "Reddit r/CryptoCurrency",
        "subreddit": "CryptoCurrency",
        "sort": "new",
        "limit": 20,
        "refresh_interval": 600,
    },
]
