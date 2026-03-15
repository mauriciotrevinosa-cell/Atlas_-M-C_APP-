"""
Signal — a normalized market signal from any source.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class SignalCategory(str, Enum):
    EARNINGS  = "earnings"    # earnings calls, guidance, EPS beats/misses
    MACRO     = "macro"       # fed decisions, CPI, jobs reports
    SENTIMENT = "sentiment"   # social/community opinion
    TECHNICAL = "technical"   # chart patterns, levels, indicators
    WHALE     = "whale"       # large transactions, dark pool, unusual options
    NEWS      = "news"        # general market news
    CRYPTO    = "crypto"      # crypto-specific events
    UNKNOWN   = "unknown"


class Sentiment(str, Enum):
    BULLISH  = "bullish"
    BEARISH  = "bearish"
    NEUTRAL  = "neutral"


class Urgency(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class Signal(BaseModel):
    id:            str      = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id:     str
    raw_id:        str      = ""     # original ID/GUID from the source
    url:           Optional[str] = None
    title:         str
    body:          Optional[str] = None
    author:        Optional[str] = None
    published_at:  datetime
    collected_at:  datetime  = Field(default_factory=datetime.utcnow)

    # Classification
    category:        SignalCategory = SignalCategory.UNKNOWN
    sentiment:       Sentiment      = Sentiment.NEUTRAL
    sentiment_score: float          = 0.0   # -1.0 (very bearish) … +1.0 (very bullish)

    # Ticker / keyword extraction
    tickers:  List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    tags:     List[str] = Field(default_factory=list)

    # Deduplication fingerprint
    content_hash: str = ""   # SHA256(source_id + url + title[:120])

    # Scoring
    relevance_score: float  = 0.0   # 0.0 … 1.0
    urgency:         Urgency = Urgency.LOW

    class Config:
        use_enum_values = True
