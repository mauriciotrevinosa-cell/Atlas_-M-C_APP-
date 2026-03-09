"""
Macro Signal Aggregator
========================
Combines NLP sentiment signals from all sources into a unified
macro sentiment score that ARIA and the Swarm can consume.

Provides:
  MacroSignal     — final quantitative output consumed by ARIA
  MacroAggregator — orchestrates news, FED, social → macro score

The macro score feeds into:
  - SwarmCoordinator.decide() as market_context
  - Risk weighting adjustments
  - Position sizing modifiers

Score scale: −1.0 (extreme bearish) → +1.0 (extreme bullish)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .sentiment_engine import SentimentEngine, SentimentSignal, MacroSentimentSummary
from .news_ingestion   import NewsIngestion

logger = logging.getLogger("atlas.nlp.macro_signal")


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class MacroSignal:
    """
    Unified macro sentiment output for consumption by ARIA and the Swarm.

    risk_adjustment: multiplier applied to position sizing (0.5 = half size, 1.2 = 20% larger)
    """
    timestamp: float = field(default_factory=time.time)
    overall_score: float = 0.0        # −1 to +1
    overall_label: str = "NEUTRAL"
    news_score: float = 0.0
    fed_score: float = 0.0
    social_score: float = 0.0
    risk_adjustment: float = 1.0      # position size modifier
    regime: str = "NORMAL"           # RISK_ON / NORMAL / RISK_OFF / CRISIS
    fed_stance: str = "NEUTRAL"      # HAWKISH / NEUTRAL / DOVISH
    top_themes: List[str] = field(default_factory=list)
    top_tickers: List[str] = field(default_factory=list)
    market_implication: str = ""
    raw_signals: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "timestamp":          self.timestamp,
            "overall_score":      round(self.overall_score, 4),
            "overall_label":      self.overall_label,
            "scores": {
                "news":   round(self.news_score, 4),
                "fed":    round(self.fed_score, 4),
                "social": round(self.social_score, 4),
            },
            "risk_adjustment":    round(self.risk_adjustment, 3),
            "regime":             self.regime,
            "fed_stance":         self.fed_stance,
            "top_themes":         self.top_themes,
            "top_tickers":        self.top_tickers,
            "market_implication": self.market_implication,
            "raw_signals":        self.raw_signals,
        }

    def summary_line(self) -> str:
        return (
            f"MacroSignal [{self.overall_label}] "
            f"score={self.overall_score:+.3f} | "
            f"regime={self.regime} | fed={self.fed_stance} | "
            f"risk_adj={self.risk_adjustment:.2f}x | "
            f"themes={','.join(self.top_themes[:3])}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  MacroAggregator
# ══════════════════════════════════════════════════════════════════════════════

class MacroAggregator:
    """
    Orchestrates all NLP sources into a unified MacroSignal.

    Usage:
        agg = MacroAggregator()

        # Full auto-fetch from news RSS
        macro = agg.run()
        print(macro.summary_line())

        # With custom FED statement text
        macro = agg.run(fed_text="The Committee decided to maintain the target range...")
        print(macro.to_dict())

        # With social posts
        macro = agg.run(social_posts=["$SPY puts", "Market crash incoming 📉"])
        print(macro.regime)
    """

    # Source weights for overall score
    WEIGHTS = {"news": 0.50, "fed": 0.30, "social": 0.20}

    def __init__(
        self,
        auto_fetch_news: bool = True,
        cache_ttl: int = 300,
    ):
        self.auto_fetch_news = auto_fetch_news
        self.nlp_engine      = SentimentEngine()
        self.news_ingestion  = NewsIngestion(cache_ttl=cache_ttl) if auto_fetch_news else None
        self._last_result: Optional[MacroSignal] = None
        logger.info("MacroAggregator initialised (auto_fetch=%s)", auto_fetch_news)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        news_texts: Optional[List[str]] = None,
        fed_text: Optional[str] = None,
        social_posts: Optional[List[str]] = None,
        social_scores: Optional[List[float]] = None,
        ticker_context: Optional[str] = None,
    ) -> MacroSignal:
        """
        Run full macro aggregation pipeline.

        Parameters
        ----------
        news_texts    : Optional list of news headline/article texts (override auto-fetch)
        fed_text      : FED minutes or statement text
        social_posts  : List of social media post texts
        social_scores : Engagement weights for social posts (0–1 each)
        ticker_context: Optional ticker for context

        Returns MacroSignal.
        """
        all_signals: List[SentimentSignal] = []

        # ── News signals ─────────────────────────────────────────────────────
        if news_texts:
            result = NewsIngestion().ingest_custom(news_texts, source="news", ticker=ticker_context or "")
            all_signals.extend(result.signals)
        elif self.auto_fetch_news and self.news_ingestion:
            try:
                if ticker_context:
                    result = self.news_ingestion.fetch_ticker_news(ticker_context)
                else:
                    result = self.news_ingestion.fetch_market_news()
                all_signals.extend(result.signals)
                logger.debug("News: %d signals fetched", len(result.signals))
            except Exception as exc:
                logger.warning("Auto news fetch failed: %s", exc)

        # ── FED signals ───────────────────────────────────────────────────────
        if fed_text:
            fed_sig = self.nlp_engine.analyse(fed_text, source="fed")
            all_signals.append(fed_sig)
            logger.debug("FED signal: score=%.3f label=%s", fed_sig.adjusted_score, fed_sig.label)

        # ── Social signals ────────────────────────────────────────────────────
        if social_posts:
            eng = social_scores or [1.0] * len(social_posts)
            social_sigs = self.nlp_engine.batch_analyse(
                social_posts, source="social", engagement_scores=eng
            )
            all_signals.extend(social_sigs)
            logger.debug("Social: %d signals", len(social_sigs))

        # ── Aggregate ─────────────────────────────────────────────────────────
        if not all_signals:
            logger.warning("No signals available — returning neutral MacroSignal")
            return MacroSignal()

        summary = self.nlp_engine.summarise(all_signals, weights=self.WEIGHTS)
        macro   = self._build_macro_signal(summary)
        self._last_result = macro

        logger.info(macro.summary_line())
        return macro

    def last(self) -> Optional[MacroSignal]:
        """Return the last computed MacroSignal (without re-fetching)."""
        return self._last_result

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_macro_signal(self, summary: MacroSentimentSummary) -> MacroSignal:
        signal = MacroSignal()
        signal.overall_score      = summary.overall_score
        signal.overall_label      = summary.overall_label
        signal.news_score         = summary.news_score
        signal.fed_score          = summary.fed_score
        signal.social_score       = summary.social_score
        signal.top_themes         = summary.top_themes
        signal.top_tickers        = summary.top_entities[:8]
        signal.market_implication = summary.market_implication
        signal.raw_signals        = summary.n_documents

        signal.regime       = self._classify_regime(signal)
        signal.fed_stance   = self._fed_stance(signal.fed_score)
        signal.risk_adjustment = self._risk_adjustment(signal)

        return signal

    @staticmethod
    def _classify_regime(sig: MacroSignal) -> str:
        score = sig.overall_score
        if score >= 0.40:
            return "RISK_ON"
        elif score >= 0.10:
            return "NORMAL"
        elif score >= -0.30:
            return "RISK_OFF"
        return "CRISIS"

    @staticmethod
    def _fed_stance(fed_score: float) -> str:
        if fed_score >= 0.20:
            return "DOVISH"
        elif fed_score <= -0.20:
            return "HAWKISH"
        return "NEUTRAL"

    @staticmethod
    def _risk_adjustment(sig: MacroSignal) -> float:
        """
        Position size multiplier:
          RISK_ON  → 1.15 (allow 15% larger positions)
          NORMAL   → 1.00
          RISK_OFF → 0.75 (reduce positions)
          CRISIS   → 0.40 (drastically cut)
        """
        return {
            "RISK_ON":  1.15,
            "NORMAL":   1.00,
            "RISK_OFF": 0.75,
            "CRISIS":   0.40,
        }.get(sig.regime, 1.00)
