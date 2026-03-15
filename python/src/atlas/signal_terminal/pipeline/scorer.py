"""
Scorer — computes relevance_score and urgency for a Signal.

Factors:
  • recency    : newer signals score higher (decay over 24h)
  • sentiment  : stronger sentiment → higher score
  • matches    : more watchlist matches → higher score
  • category   : whale / earnings / macro score higher than generic news
  • reddit meta: post score + upvote_ratio (if available in extra)
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import List

from ..models import Match, Signal, SignalCategory, Urgency
from .. import config as cfg


_CAT_BOOST = {
    SignalCategory.WHALE:     0.25,
    SignalCategory.EARNINGS:  0.20,
    SignalCategory.MACRO:     0.15,
    SignalCategory.TECHNICAL: 0.10,
    SignalCategory.CRYPTO:    0.10,
    SignalCategory.SENTIMENT: 0.05,
    SignalCategory.NEWS:      0.00,
    SignalCategory.UNKNOWN:  -0.05,
}


def _hours_old(sig: Signal) -> float:
    now = datetime.utcnow()
    pub = sig.published_at
    # ensure no tzinfo
    if pub.tzinfo is not None:
        pub = pub.replace(tzinfo=None)
    delta = (now - pub).total_seconds() / 3600
    return max(0.0, delta)


def _recency_score(hours: float, decay_h: float = 24.0) -> float:
    """Exponential decay: 1.0 at 0h, ~0.37 at decay_h, near 0 beyond."""
    return math.exp(-hours / decay_h)


class Scorer:
    def score(self, sig: Signal, matches: List[Match]) -> Signal:
        hours   = _hours_old(sig)
        recency = _recency_score(hours, cfg.RELEVANCE_DECAY_HOURS)

        # Sentiment magnitude (0 → 1)
        sentiment_mag = abs(sig.sentiment_score)

        # Category boost
        cat_boost = _CAT_BOOST.get(sig.category, 0.0)

        # Match boost: each watchlist hit adds 0.1 (capped at 0.3)
        match_boost = min(len(matches) * 0.10, 0.30)

        score = recency * 0.40 + sentiment_mag * 0.25 + cat_boost + match_boost
        score = max(0.0, min(1.0, score))

        sig.relevance_score = round(score, 4)
        sig.urgency = _urgency(sig, hours, matches)
        return sig


def _urgency(sig: Signal, hours: float, matches: List[Match]) -> Urgency:
    if sig.category == SignalCategory.WHALE and sig.relevance_score >= 0.7:
        return Urgency.CRITICAL
    if sig.category in (SignalCategory.EARNINGS, SignalCategory.MACRO) and hours < 2:
        return Urgency.HIGH
    if matches and sig.relevance_score >= cfg.HIGH_RELEVANCE_THRESHOLD:
        return Urgency.HIGH
    if sig.relevance_score >= 0.5 or (matches and hours < 6):
        return Urgency.MEDIUM
    return Urgency.LOW
