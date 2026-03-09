"""
Atlas NLP — Macro & Social Sentiment Intelligence
===================================================
Converts unstructured financial text into quantitative signals.

Modules:
  sentiment_engine  — core lexicon + FED + social sentiment pipeline
  news_ingestion    — RSS/API news fetching and deduplication
  macro_signal      — unified macro sentiment aggregator for ARIA

Quick-start:
    from atlas.nlp import MacroAggregator, SentimentEngine

    # Full macro run (fetches RSS news automatically)
    agg   = MacroAggregator()
    macro = agg.run(fed_text="...", social_posts=["..."])
    print(macro.summary_line())

    # Single text
    engine = SentimentEngine()
    sig = engine.analyse("AAPL beats Q3 earnings by 15%", source="news")
    print(sig.label, sig.adjusted_score)

Copyright (c) 2026 M&C. All rights reserved.
"""

from .sentiment_engine import (
    SentimentEngine,
    SentimentSignal,
    MacroSentimentSummary,
    LexiconScorer,
    FedMinutesAnalyser,
    SocialSentimentAnalyser,
    EntityExtractor,
    TextPreprocessor,
)
from .news_ingestion import (
    NewsIngestion,
    NewsArticle,
    NewsIngestResult,
    RSSParser,
)
from .macro_signal import (
    MacroAggregator,
    MacroSignal,
)

__all__ = [
    # Core NLP
    "SentimentEngine", "SentimentSignal", "MacroSentimentSummary",
    "LexiconScorer", "FedMinutesAnalyser", "SocialSentimentAnalyser",
    "EntityExtractor", "TextPreprocessor",
    # News
    "NewsIngestion", "NewsArticle", "NewsIngestResult", "RSSParser",
    # Macro
    "MacroAggregator", "MacroSignal",
]
