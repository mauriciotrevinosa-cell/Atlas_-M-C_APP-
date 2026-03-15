"""
Classifier — assigns category and sentiment to a Signal.
Rule-based keyword approach: no ML dependency, deterministic, extensible.
"""
from __future__ import annotations
import re
from typing import List, Tuple

from ..models import Signal, SignalCategory, Sentiment

# ── Category keyword sets ─────────────────────────────────────────────────

_CAT_RULES: List[Tuple[SignalCategory, List[str]]] = [
    (SignalCategory.EARNINGS, [
        "earnings", "eps", "revenue", "guidance", "beat", "miss", "quarter",
        "q1", "q2", "q3", "q4", "fiscal", "profit", "net income", "per share",
        "ebitda", "operating income",
    ]),
    (SignalCategory.MACRO, [
        "federal reserve", "fed rate", "interest rate", "cpi", "inflation",
        "gdp", "jobs report", "unemployment", "nonfarm", "payroll", "fomc",
        "powell", "central bank", "treasury", "yield curve", "recession",
        "stimulus", "quantitative easing", "qe", "tapering",
    ]),
    (SignalCategory.WHALE, [
        "whale", "dark pool", "unusual options", "block trade", "insider",
        "institutional", "13f", "form 4", "sec filing", "short interest",
        "short squeeze", "large position", "accumulation", "distribution",
        "hedge fund",
    ]),
    (SignalCategory.TECHNICAL, [
        "support", "resistance", "breakout", "breakdown", "moving average",
        "rsi", "macd", "bollinger", "fibonacci", "chart pattern", "wedge",
        "flag", "cup and handle", "double top", "double bottom", "head and shoulders",
        "oversold", "overbought", "volume spike",
    ]),
    (SignalCategory.CRYPTO, [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi",
        "nft", "altcoin", "stablecoin", "halving", "mining", "wallet",
        "exchange hack", "binance", "coinbase", "layer 2",
    ]),
    (SignalCategory.SENTIMENT, [
        "sentiment", "social media", "reddit", "twitter", "wallstreetbets",
        "retail investor", "meme stock", "trend", "popular", "trending",
        "community", "forum", "buzz",
    ]),
]

# ── Sentiment keyword sets ────────────────────────────────────────────────

_BULLISH_WORDS = [
    "surge", "soar", "rally", "gain", "rise", "up", "high", "bull", "bullish",
    "strong", "beat", "outperform", "upgrade", "buy", "long", "positive",
    "profit", "record", "all-time high", "ath", "moon", "pump", "growth",
    "expansion", "recovery", "rebound", "breakout",
]

_BEARISH_WORDS = [
    "drop", "fall", "decline", "crash", "plunge", "down", "low", "bear", "bearish",
    "weak", "miss", "underperform", "downgrade", "sell", "short", "negative",
    "loss", "warning", "risk", "dump", "correction", "recession", "default",
    "bankruptcy", "concern", "fear", "panic", "liquidate",
]

_WORD_RE = re.compile(r"\b\w+\b")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]


def _score_sentiment(tokens: List[str]) -> Tuple[Sentiment, float]:
    bull = sum(1 for t in tokens if t in _BULLISH_WORDS)
    bear = sum(1 for t in tokens if t in _BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return Sentiment.NEUTRAL, 0.0
    score = (bull - bear) / total          # -1.0 … +1.0
    if score > 0.15:
        return Sentiment.BULLISH, round(score, 3)
    if score < -0.15:
        return Sentiment.BEARISH, round(score, 3)
    return Sentiment.NEUTRAL, round(score, 3)


def _detect_category(tokens: List[str], full_text: str) -> SignalCategory:
    text_lower = full_text.lower()
    for cat, keywords in _CAT_RULES:
        for kw in keywords:
            if kw in text_lower:
                return cat
    return SignalCategory.NEWS


class Classifier:
    """Assign category, sentiment, and sentiment_score to a Signal (mutates in place)."""

    def classify(self, sig: Signal) -> Signal:
        full_text = f"{sig.title} {sig.body or ''}"
        tokens    = _tokenize(full_text)

        sig.category        = _detect_category(tokens, full_text)
        sig.sentiment, sig.sentiment_score = _score_sentiment(tokens)

        # Extract keywords (top recurring non-stop content words)
        sig.keywords = _top_keywords(tokens)

        return sig


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "it", "its", "as", "by", "from", "up", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "then", "just", "now", "not", "no", "so", "if", "i",
    "my", "we", "our", "you", "your", "he", "she", "they", "their",
    "what", "which", "who", "when", "where", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "than",
    "too", "very", "s", "t", "re", "ve", "ll", "d", "m",
}


def _top_keywords(tokens: List[str], n: int = 10) -> List[str]:
    from collections import Counter
    counts = Counter(t for t in tokens if len(t) > 3 and t not in _STOPWORDS)
    return [w for w, _ in counts.most_common(n)]
