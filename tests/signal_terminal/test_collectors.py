"""
Tests — Signal Terminal collectors (unit tests with mocking)
"""
from __future__ import annotations
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from atlas.signal_terminal.models import Source, SourceType
from atlas.signal_terminal.collectors.rss_collector import RSSCollector, _parse_date
from atlas.signal_terminal.collectors.reddit_collector import RedditCollector


def _source(src_type=SourceType.RSS, url="https://example.com/feed.rss", **cfg):
    return Source(id="s1", name="Test Source", type=src_type, url=url, config=cfg)


# ── Date parsing ─────────────────────────────────────────────────────────

def test_parse_rfc2822_date():
    dt = _parse_date("Thu, 01 Jan 2026 12:00:00 GMT")
    assert dt is not None
    assert dt.year == 2026

def test_parse_iso_date():
    dt = _parse_date("2026-01-15T08:30:00Z")
    assert dt is not None
    assert dt.month == 1

def test_parse_none_returns_none():
    assert _parse_date(None) is None

def test_parse_empty_returns_none():
    assert _parse_date("") is None


# ── RSS Collector ─────────────────────────────────────────────────────────

class TestRSSCollector:
    SAMPLE_RSS = b"""<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <title>Finance News</title>
        <item>
          <title>AAPL stock surges on earnings beat</title>
          <link>https://example.com/aapl</link>
          <guid>guid-001</guid>
          <description>Apple beats EPS estimates for Q3 2025.</description>
          <pubDate>Mon, 01 Jan 2026 10:00:00 GMT</pubDate>
        </item>
        <item>
          <title>Fed holds rates steady</title>
          <link>https://example.com/fed</link>
          <guid>guid-002</guid>
          <description>Federal Reserve keeps rates unchanged.</description>
          <pubDate>Mon, 01 Jan 2026 09:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    def test_stdlib_fallback_parse(self):
        src = _source()
        col = RSSCollector(src)
        with patch("urllib.request.urlopen") as mock_open:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=self.SAMPLE_RSS)))
            mock_ctx.__exit__  = MagicMock(return_value=False)
            mock_open.return_value = mock_ctx
            items = col._fetch_stdlib("https://example.com/feed.rss")

        assert len(items) == 2
        assert items[0].title == "AAPL stock surges on earnings beat"
        assert items[0].url   == "https://example.com/aapl"
        assert items[0].raw_id == "guid-001"
        assert items[1].title  == "Fed holds rates steady"

    def test_empty_feed_returns_empty_list(self):
        src = _source()
        col = RSSCollector(src)
        with patch("urllib.request.urlopen") as mock_open:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=MagicMock(
                read=MagicMock(return_value=b"<rss><channel></channel></rss>")
            ))
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_ctx
            items = col._fetch_stdlib("https://example.com/feed.rss")
        assert items == []

    def test_network_error_returns_empty_list(self):
        src = _source()
        col = RSSCollector(src)
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            items = col._fetch_stdlib("https://example.com/feed.rss")
        assert items == []


# ── Reddit Collector ──────────────────────────────────────────────────────

class TestRedditCollector:
    SAMPLE_LISTING = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "$TSLA unusual options activity detected",
                        "selftext": "Somebody bought 10,000 TSLA call options today...",
                        "permalink": "/r/stocks/comments/abc123/tsla_options",
                        "author": "optionsguru",
                        "created_utc": 1735689600.0,
                        "score": 150,
                        "upvote_ratio": 0.92,
                        "num_comments": 42,
                        "is_self": True,
                        "link_flair_text": "DD",
                    }
                }
            ]
        }
    }

    def test_parse_listing(self):
        src = _source(src_type=SourceType.REDDIT, subreddit="stocks")
        col = RedditCollector(src)
        items = col._parse_listing(self.SAMPLE_LISTING, "stocks")
        assert len(items) == 1
        item = items[0]
        assert item.raw_id   == "abc123"
        assert "$TSLA" in item.title
        assert item.extra["score"] == 150
        assert item.extra["subreddit"] == "stocks"

    def test_empty_listing(self):
        src = _source(src_type=SourceType.REDDIT, subreddit="stocks")
        col = RedditCollector(src)
        items = col._parse_listing({"data": {"children": []}}, "stocks")
        assert items == []
