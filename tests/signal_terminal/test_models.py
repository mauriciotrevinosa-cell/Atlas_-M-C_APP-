"""
Tests — Signal Terminal domain models
"""
from __future__ import annotations
import pytest
from datetime import datetime

from atlas.signal_terminal.models import (
    Signal, SignalCategory, Sentiment, Urgency,
    Source, SourceType,
    Match, MatchType,
    AlertRule, AlertAction,
    WhaleEvent, WhaleEventType,
    WatchlistItem, AssetType, WatchPriority,
)


class TestSignal:
    def test_defaults(self):
        sig = Signal(source_id="s1", title="Test", published_at=datetime.utcnow())
        assert sig.id != ""
        assert sig.category == SignalCategory.UNKNOWN
        assert sig.sentiment == Sentiment.NEUTRAL
        assert sig.sentiment_score == 0.0
        assert sig.tickers == []
        assert sig.urgency == Urgency.LOW

    def test_id_unique(self):
        s1 = Signal(source_id="s", title="T", published_at=datetime.utcnow())
        s2 = Signal(source_id="s", title="T", published_at=datetime.utcnow())
        assert s1.id != s2.id


class TestWatchlistItem:
    def test_defaults(self):
        item = WatchlistItem(ticker="aapl")
        assert item.ticker == "aapl"
        assert item.asset_type == AssetType.STOCK
        assert item.priority == WatchPriority.MEDIUM
        assert item.alert_enabled is True
        assert item.aliases == []

    def test_id_unique(self):
        a = WatchlistItem(ticker="AAPL")
        b = WatchlistItem(ticker="AAPL")
        assert a.id != b.id


class TestWhaleEvent:
    def test_size_label_auto(self):
        evt = WhaleEvent(ticker="AAPL", size=50_000_000)
        assert evt.size_label == "$50M+"

    def test_size_label_billion(self):
        evt = WhaleEvent(ticker="TSLA", size=1_500_000_000)
        assert evt.size_label == "$1B+"

    def test_size_label_unknown(self):
        evt = WhaleEvent(ticker="SPY", size=None)
        assert evt.size_label == "unknown"


class TestAlertRule:
    def test_defaults(self):
        rule = AlertRule(name="Test Rule", conditions={"ticker": "AAPL"})
        assert rule.enabled is True
        assert rule.action == AlertAction.LOG
        assert rule.trigger_count == 0

    def test_id_unique(self):
        r1 = AlertRule(name="R1", conditions={})
        r2 = AlertRule(name="R2", conditions={})
        assert r1.id != r2.id


class TestSource:
    def test_defaults(self):
        src = Source(name="Yahoo RSS", type=SourceType.RSS, url="https://example.com/rss")
        assert src.enabled is True
        assert src.error_count == 0
        assert src.config == {}
