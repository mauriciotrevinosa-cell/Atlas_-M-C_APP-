"""
Tests — Signal Terminal pipeline
"""
from __future__ import annotations
import pytest
from datetime import datetime

from atlas.signal_terminal.collectors.base import RawItem
from atlas.signal_terminal.pipeline.normalizer import Normalizer, _hash
from atlas.signal_terminal.pipeline.classifier import Classifier, _score_sentiment, _tokenize
from atlas.signal_terminal.pipeline.scorer import Scorer
from atlas.signal_terminal.models import Signal, SignalCategory, Sentiment, Urgency


# ── Normalizer ────────────────────────────────────────────────────────────

class TestNormalizer:
    def setup_method(self):
        self.n = Normalizer()

    def _raw(self, **kwargs):
        defaults = dict(
            source_id="test_src",
            raw_id="raw1",
            title="$AAPL beats Q3 earnings expectations",
            body="Apple reported $1.26 EPS vs $1.18 expected.",
            url="https://example.com/aapl",
            published_at=datetime.utcnow(),
        )
        defaults.update(kwargs)
        return RawItem(**defaults)

    def test_normalizes_basic(self):
        sig = self.n.normalize(self._raw())
        assert sig.title == "$AAPL beats Q3 earnings expectations"
        assert sig.source_id == "test_src"
        assert isinstance(sig.published_at, datetime)
        assert sig.content_hash != ""

    def test_cashtag_extraction(self):
        sig = self.n.normalize(self._raw(title="$AAPL and $MSFT surge today"))
        assert "AAPL" in sig.tickers
        assert "MSFT" in sig.tickers

    def test_dedup_hash_stable(self):
        h1 = _hash("src", "https://x.com", "Same title")
        h2 = _hash("src", "https://x.com", "Same title")
        assert h1 == h2

    def test_dedup_hash_differs_on_source(self):
        h1 = _hash("src1", "https://x.com", "title")
        h2 = _hash("src2", "https://x.com", "title")
        assert h1 != h2

    def test_strips_html(self):
        sig = self.n.normalize(self._raw(body="<b>Markets surge</b> today <br/>hello"))
        assert "<b>" not in sig.body
        assert "Markets surge" in sig.body


# ── Classifier ────────────────────────────────────────────────────────────

class TestClassifier:
    def setup_method(self):
        self.c = Classifier()

    def _sig(self, title: str, body: str = "") -> Signal:
        return Signal(
            source_id="test", title=title, body=body,
            published_at=datetime.utcnow(),
        )

    def test_earnings_category(self):
        sig = self._sig("Apple Q3 earnings beat EPS estimates")
        self.c.classify(sig)
        assert sig.category == SignalCategory.EARNINGS

    def test_macro_category(self):
        sig = self._sig("Federal Reserve raises interest rate by 25bps")
        self.c.classify(sig)
        assert sig.category == SignalCategory.MACRO

    def test_whale_category(self):
        sig = self._sig("Unusual options activity detected on TSLA")
        self.c.classify(sig)
        assert sig.category == SignalCategory.WHALE

    def test_bullish_sentiment(self):
        tokens = _tokenize("stock surges rally gain breakout record high")
        sent, score = _score_sentiment(tokens)
        assert sent == Sentiment.BULLISH
        assert score > 0

    def test_bearish_sentiment(self):
        tokens = _tokenize("market crash drop plunge loss sell bear")
        sent, score = _score_sentiment(tokens)
        assert sent == Sentiment.BEARISH
        assert score < 0

    def test_neutral_sentiment(self):
        sig = self._sig("Company files quarterly report with SEC")
        self.c.classify(sig)
        assert sig.sentiment == Sentiment.NEUTRAL


# ── Scorer ────────────────────────────────────────────────────────────────

class TestScorer:
    def setup_method(self):
        self.s = Scorer()

    def _sig(self, **kwargs) -> Signal:
        defaults = dict(
            source_id="test", title="Test signal",
            published_at=datetime.utcnow(),
            sentiment_score=0.5,
            category=SignalCategory.EARNINGS,
        )
        defaults.update(kwargs)
        return Signal(**defaults)

    def test_score_range(self):
        sig = self._sig()
        self.s.score(sig, [])
        assert 0.0 <= sig.relevance_score <= 1.0

    def test_whale_gets_high_urgency(self):
        sig = self._sig(
            category=SignalCategory.WHALE,
            relevance_score=0.0,   # scorer will recalculate
            sentiment_score=0.8,
        )
        self.s.score(sig, [])
        # Whale category boost pushes score up
        assert sig.relevance_score > 0.3

    def test_old_signal_lower_score(self):
        from datetime import timedelta
        fresh = self._sig(published_at=datetime.utcnow())
        old   = self._sig(published_at=datetime.utcnow() - timedelta(hours=48))
        self.s.score(fresh, [])
        self.s.score(old, [])
        assert fresh.relevance_score > old.relevance_score


# ── Integration smoke test ────────────────────────────────────────────────

def test_full_pipeline_smoke(tmp_path):
    """End-to-end: RawItem → Signal stored in DB."""
    from atlas.signal_terminal.storage.repository import SignalRepository
    from atlas.signal_terminal.services.alert_service import AlertService
    from atlas.signal_terminal.services.whale_service import WhaleService
    from atlas.signal_terminal.services.signal_service import SignalService
    from atlas.signal_terminal.models import WatchlistItem

    db_path = tmp_path / "test.db"
    repo    = SignalRepository(db_path)
    alert   = AlertService(repo)
    whale   = WhaleService(repo)
    svc     = SignalService(repo, alert, whale)

    # Seed watchlist
    repo.upsert_watchlist_item(WatchlistItem(ticker="AAPL", name="Apple"))

    raw = RawItem(
        source_id="test_src",
        raw_id="r1",
        title="$AAPL Q3 earnings beat estimates — stock surges",
        body="Apple reported $1.26 EPS, beating the $1.18 consensus.",
        url="https://example.com/1",
        published_at=datetime.utcnow(),
    )

    inserted, dupes = svc.ingest([raw])
    assert inserted == 1
    assert dupes == 0

    # Dedup: same item again should be skipped
    inserted2, dupes2 = svc.ingest([raw])
    assert inserted2 == 0
    assert dupes2 == 1

    # Query
    signals = svc.query(ticker="AAPL")
    assert len(signals) == 1
    assert "AAPL" in signals[0].tickers

    # Stats
    stats = svc.get_stats()
    assert stats["total_signals"] == 1
    assert stats["watchlist_items"] == 1
