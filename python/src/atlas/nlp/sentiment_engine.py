"""
Sentiment Engine — Macro & Social NLP Core
============================================
Converts unstructured text (news, FED minutes, social posts) into
quantitative sentiment scores that feed ARIA's decision pipeline.

Architecture:
  TextPreprocessor  → cleans and tokenises raw text
  LexiconScorer     → finance-domain lexicon (Loughran-McDonald inspired)
  EntityExtractor   → identifies tickers, sectors, macro entities
  SentimentEngine   → orchestrates pipeline, returns SentimentSignal

Sentiment output (−1 to +1):
  +1.0 = maximum bullish
   0.0 = neutral
  −1.0 = maximum bearish

Sources supported:
  - News headlines / articles
  - FED FOMC minutes / statements
  - Reddit WSB / financial posts
  - Twitter/X financial commentary (text feed)
  - Earnings call transcripts

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("atlas.nlp.sentiment_engine")


# ══════════════════════════════════════════════════════════════════════════════
#  Finance-Domain Lexicon (Loughran-McDonald inspired)
# ══════════════════════════════════════════════════════════════════════════════

BULLISH_WORDS = {
    # Growth / positive results
    "beat", "beats", "exceed", "exceeds", "exceeded", "outperform", "outperformed",
    "upgrade", "upgraded", "upside", "growth", "grew", "accelerat", "expand",
    "record", "surge", "surged", "rally", "rallied", "gain", "gains", "gained",
    "profit", "profits", "profitable", "revenue", "revenues", "strong", "strength",
    "robust", "solid", "positive", "optimistic", "bullish", "breakout",
    "recover", "recovery", "rebound", "momentum", "opportunity", "opportunities",
    "innovative", "innovation", "demand", "partnership", "acquisition", "merger",
    "buyback", "dividend", "guidance", "raise", "raised", "higher", "increase",
    "increased", "improving", "improved", "significant", "successful", "success",
    "affirm", "affirmed", "confident", "confidence", "buy", "overweight",
    "accumulate", "green", "boom", "soar", "soared", "milestone", "breakthrough",
    # FED hawkish-turned-dovish
    "pause", "cut", "cuts", "easing", "accommodative", "dovish", "stimulus",
    "liquidity", "support",
}

BEARISH_WORDS = {
    # Negative results / risk
    "miss", "missed", "below", "disappoint", "disappointed", "disappointing",
    "downgrade", "downgraded", "downside", "decline", "declined", "fall", "fell",
    "drop", "dropped", "loss", "losses", "weak", "weakness", "poor", "negative",
    "bearish", "breakdown", "selloff", "sell-off", "crash", "collapse", "plunge",
    "plunged", "struggle", "struggling", "concern", "concerns", "risk", "risks",
    "risky", "uncertain", "uncertainty", "volatile", "volatility", "headwind",
    "headwinds", "layoff", "layoffs", "restructur", "writedown", "write-down",
    "impair", "impairment", "warning", "cut", "cuts", "lower", "lowered",
    "reduce", "reduced", "recession", "slowdown", "contraction", "deficit",
    "debt", "leverage", "default", "bankrupt", "bankruptcy", "lawsuit", "fine",
    "penalty", "investigation", "fraud", "probe", "sell", "underweight", "avoid",
    # FED hawkish signals
    "hike", "hikes", "tighten", "tightening", "hawkish", "restrictive",
    "inflation", "inflationary", "stagflation",
}

INTENSIFIERS = {
    "very", "highly", "extremely", "significantly", "substantially", "sharply",
    "dramatically", "massively", "strongly", "deeply",
}

NEGATORS = {
    "not", "no", "never", "neither", "nor", "cannot", "can't", "won't",
    "wouldn't", "shouldn't", "didn't", "doesn't", "isn't", "wasn't",
    "aren't", "weren't", "without", "lack", "lacking", "fail", "failed",
}

# FED-specific vocabulary
FED_HAWKISH_PHRASES = [
    "remain vigilant", "further tightening", "persistently elevated",
    "not yet confident", "higher for longer", "additional increases",
    "labor market remains tight", "inflation well above target",
]

FED_DOVISH_PHRASES = [
    "inflation has eased", "cooling labor market", "appropriate to ease",
    "rate cuts", "accommodative stance", "reducing the target range",
    "inflation moving toward", "economy is moderating",
    "achieving maximum employment", "price stability achieved",
]


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class SentimentSignal:
    """Quantitative sentiment output for a single text document."""
    source_type: str           # news / fed / social / transcript
    raw_score: float = 0.0    # −1 to +1 (lexicon score)
    adjusted_score: float = 0.0  # after entity boosting & normalisation
    confidence: float = 0.5   # 0–1 (coverage / text length quality)
    label: str = "NEUTRAL"    # BULLISH / MILDLY_BULLISH / NEUTRAL / MILDLY_BEARISH / BEARISH
    entities: List[str] = field(default_factory=list)    # tickers/entities found
    sector_tags: List[str] = field(default_factory=list) # sectors mentioned
    key_phrases: List[str] = field(default_factory=list) # high-signal phrases
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "source_type":     self.source_type,
            "raw_score":       round(self.raw_score, 4),
            "adjusted_score":  round(self.adjusted_score, 4),
            "confidence":      round(self.confidence, 3),
            "label":           self.label,
            "entities":        self.entities,
            "sector_tags":     self.sector_tags,
            "key_phrases":     self.key_phrases[:5],
            "word_count":      self.word_count,
        }


@dataclass
class MacroSentimentSummary:
    """Aggregated macro sentiment across multiple documents."""
    overall_score: float = 0.0
    overall_label: str = "NEUTRAL"
    news_score: float = 0.0
    fed_score: float = 0.0
    social_score: float = 0.0
    n_documents: int = 0
    top_entities: List[str] = field(default_factory=list)
    top_themes: List[str] = field(default_factory=list)
    signals: List[SentimentSignal] = field(default_factory=list)
    market_implication: str = ""

    def to_dict(self) -> Dict:
        return {
            "overall_score":       round(self.overall_score, 4),
            "overall_label":       self.overall_label,
            "by_source": {
                "news":   round(self.news_score, 4),
                "fed":    round(self.fed_score, 4),
                "social": round(self.social_score, 4),
            },
            "n_documents":         self.n_documents,
            "top_entities":        self.top_entities[:10],
            "top_themes":          self.top_themes[:5],
            "market_implication":  self.market_implication,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Text Preprocessor
# ══════════════════════════════════════════════════════════════════════════════

class TextPreprocessor:
    """Cleans and tokenises financial text."""

    # Remove URLs, HTML, special chars
    _URL_RE    = re.compile(r"https?://\S+|www\.\S+")
    _HTML_RE   = re.compile(r"<[^>]+>")
    _TICKER_RE = re.compile(r"\b\$([A-Z]{1,5})\b")  # $AAPL style
    _NUM_RE    = re.compile(r"\b-?\d+\.?\d*%?\b")

    def preprocess(self, text: str) -> Tuple[str, List[str]]:
        """
        Clean text and extract ticker mentions.
        Returns (cleaned_text, ticker_list).
        """
        # Extract $TICKER mentions before cleaning
        tickers = self._TICKER_RE.findall(text)

        text = self._URL_RE.sub(" ", text)
        text = self._HTML_RE.sub(" ", text)
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-\.\,\'\%]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text, [t.upper() for t in tickers]

    @staticmethod
    def tokenise(text: str) -> List[str]:
        return text.split()


# ══════════════════════════════════════════════════════════════════════════════
#  Lexicon Scorer
# ══════════════════════════════════════════════════════════════════════════════

class LexiconScorer:
    """
    Finance-domain lexicon-based sentiment scorer.
    Handles negation windows and intensifier boosting.
    """

    NEGATION_WINDOW = 3   # words following a negator get flipped
    INTENSIFIER_BOOST = 1.5

    def score(self, tokens: List[str]) -> Tuple[float, List[str]]:
        """
        Score a token list.
        Returns (raw_score, key_signal_words).
        """
        bull_hits: List[Tuple[str, float]] = []
        bear_hits: List[Tuple[str, float]] = []
        n = len(tokens)

        i = 0
        while i < n:
            tok = tokens[i]

            # Negation window
            negated = False
            for j in range(max(0, i - self.NEGATION_WINDOW), i):
                if tokens[j] in NEGATORS:
                    negated = True
                    break

            # Intensifier boost
            boost = 1.0
            if i > 0 and tokens[i - 1] in INTENSIFIERS:
                boost = self.INTENSIFIER_BOOST

            # Check lexicon
            matched_bull = any(tok.startswith(bw) for bw in BULLISH_WORDS)
            matched_bear = any(tok.startswith(bw) for bw in BEARISH_WORDS)

            if matched_bull and not negated:
                bull_hits.append((tok, boost))
            elif matched_bull and negated:
                bear_hits.append((f"NOT_{tok}", boost))
            elif matched_bear and not negated:
                bear_hits.append((tok, boost))
            elif matched_bear and negated:
                bull_hits.append((f"NOT_{tok}", boost))

            i += 1

        total_bull = sum(w for _, w in bull_hits)
        total_bear = sum(w for _, w in bear_hits)
        total = total_bull + total_bear

        if total == 0:
            return 0.0, []

        raw_score = (total_bull - total_bear) / total
        key_words = [w for w, _ in (bull_hits + bear_hits)[:8]]

        return float(raw_score), key_words


# ══════════════════════════════════════════════════════════════════════════════
#  FED Minutes Analyser
# ══════════════════════════════════════════════════════════════════════════════

class FedMinutesAnalyser:
    """
    Specialised analyser for FED FOMC minutes and statements.
    Scans for hawkish/dovish phrase patterns beyond simple lexicon.
    """

    def analyse(self, text: str) -> Tuple[float, List[str]]:
        """
        Returns (sentiment_score, matched_phrases).
        Positive = dovish (market bullish), Negative = hawkish (market bearish).
        """
        text_lower = text.lower()
        score = 0.0
        matched = []

        for phrase in FED_DOVISH_PHRASES:
            if phrase in text_lower:
                score += 0.15
                matched.append(f"[DOVISH] {phrase}")

        for phrase in FED_HAWKISH_PHRASES:
            if phrase in text_lower:
                score -= 0.15
                matched.append(f"[HAWKISH] {phrase}")

        # Count rate-related numbers for context
        rate_hike_count = len(re.findall(r"(rate hike|hike rate|increase rate)", text_lower))
        rate_cut_count  = len(re.findall(r"(rate cut|cut rate|reduce rate|lower rate)", text_lower))

        score += (rate_cut_count - rate_hike_count) * 0.08

        return float(max(-1.0, min(1.0, score))), matched


# ══════════════════════════════════════════════════════════════════════════════
#  Social Sentiment Analyser
# ══════════════════════════════════════════════════════════════════════════════

class SocialSentimentAnalyser:
    """
    Analyses Reddit/Twitter financial posts.
    Handles emoji, slang, and Reddit-specific patterns.
    """

    # Reddit WSB / financial Twitter slang
    BULL_SLANG = {
        "🚀", "🌙", "moon", "mooning", "🐂", "bull", "bullish", "calls",
        "yolo", "tendies", "gains", "apes", "hold", "hodl", "💎", "🙌",
        "buy the dip", "btd", "long", "longs", "squeeze", "gamma squeeze",
        "short squeeze", "🔥", "📈", "green", "ripping", "pumping",
    }

    BEAR_SLANG = {
        "🐻", "bear", "bearish", "puts", "short", "shorts", "dump", "dumping",
        "sell", "selling", "bag", "bagholding", "crater", "crash", "rekt",
        "📉", "red", "bleeding", "rug", "rugpull", "fud", "fear", "panic",
        "capitulate", "capitulation",
    }

    def analyse(self, text: str, engagement_score: float = 1.0) -> Tuple[float, List[str]]:
        """
        Analyse social post sentiment.
        engagement_score: likes/upvotes normalised weight (0–1).
        Returns (score, matched_terms).
        """
        text_lower = text.lower()
        bull_count = sum(1 for t in self.BULL_SLANG if t in text_lower)
        bear_count = sum(1 for t in self.BEAR_SLANG if t in text_lower)
        total = bull_count + bear_count

        if total == 0:
            return 0.0, []

        score = (bull_count - bear_count) / total
        # Engagement weight: high engagement = stronger signal
        score *= (0.5 + 0.5 * min(1.0, engagement_score))

        matched = (
            [t for t in self.BULL_SLANG if t in text_lower][:3] +
            [t for t in self.BEAR_SLANG if t in text_lower][:3]
        )
        return float(score), matched


# ══════════════════════════════════════════════════════════════════════════════
#  Sector / Entity Tagger
# ══════════════════════════════════════════════════════════════════════════════

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "TECH":       ["technology", "software", "semiconductor", "chip", "ai", "cloud", "data center", "nvidia", "microsoft", "apple", "meta", "alphabet"],
    "ENERGY":     ["oil", "gas", "energy", "opec", "crude", "natural gas", "exxon", "chevron", "refinery"],
    "FINANCIALS": ["bank", "fed", "interest rate", "credit", "mortgage", "jpmorgan", "goldman", "lending", "bonds"],
    "HEALTH":     ["pharma", "biotech", "drug", "fda", "clinical", "pfizer", "biotech", "healthcare"],
    "CONSUMER":   ["retail", "consumer", "spending", "amazon", "walmart", "ecommerce", "inflation"],
    "MACRO":      ["gdp", "inflation", "unemployment", "fed", "fomc", "treasury", "cpi", "pce", "recession"],
    "CRYPTO":     ["bitcoin", "btc", "ethereum", "crypto", "defi", "blockchain", "coinbase"],
}


class EntityExtractor:
    """Extracts sector tags and named entities from financial text."""

    # Common major ticker patterns
    _TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")

    KNOWN_TICKERS = {
        "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "TSLA",
        "JPM", "BAC", "GS", "MS", "V", "MA", "BRK", "JNJ", "PFE", "XOM",
        "CVX", "AMD", "INTC", "QCOM", "SPY", "QQQ", "IWM", "DIA", "VIX",
        "BTC", "ETH", "SOL", "BNB",
    }

    def extract(self, text: str, pre_tickers: List[str]) -> Tuple[List[str], List[str]]:
        """
        Returns (entities, sector_tags).
        """
        text_lower = text.lower()

        # Sector detection
        sectors = []
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                sectors.append(sector)

        # Entities: pre-extracted $TICKER mentions + known tickers in caps
        entities = list(set(pre_tickers))
        caps_found = self._TICKER_PATTERN.findall(text)
        for t in caps_found:
            if t in self.KNOWN_TICKERS:
                entities.append(t)

        return list(set(entities)), list(set(sectors))


# ══════════════════════════════════════════════════════════════════════════════
#  Sentiment Engine (Main Orchestrator)
# ══════════════════════════════════════════════════════════════════════════════

class SentimentEngine:
    """
    Main NLP pipeline: converts raw financial text → SentimentSignal.

    Usage:
        engine = SentimentEngine()

        # News article
        signal = engine.analyse("AAPL beats Q3 earnings, raises guidance", source="news")

        # FED minutes
        signal = engine.analyse(fed_minutes_text, source="fed")

        # Reddit post
        signal = engine.analyse("$TSLA to the moon 🚀 buying calls", source="social")

        # Batch
        summary = engine.summarise([signal1, signal2, ...])
    """

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.lexicon      = LexiconScorer()
        self.fed_analyser = FedMinutesAnalyser()
        self.social       = SocialSentimentAnalyser()
        self.entity_ex    = EntityExtractor()
        logger.info("SentimentEngine initialised")

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(
        self,
        text: str,
        source: str = "news",
        engagement_score: float = 1.0,
        ticker_context: Optional[str] = None,
    ) -> SentimentSignal:
        """
        Analyse a single text document.

        Parameters
        ----------
        text             : Raw text to analyse
        source           : 'news' | 'fed' | 'social' | 'transcript'
        engagement_score : Normalised engagement weight for social posts (0–1)
        ticker_context   : Optional ticker this text is specifically about

        Returns SentimentSignal.
        """
        signal = SentimentSignal(source_type=source)

        if not text or len(text.strip()) < 5:
            return signal

        # 1. Preprocess
        cleaned, pre_tickers = self.preprocessor.preprocess(text)
        tokens = self.preprocessor.tokenise(cleaned)
        signal.word_count = len(tokens)

        # 2. Entity extraction
        entities, sectors = self.entity_ex.extract(text, pre_tickers)
        if ticker_context:
            entities = list(set(entities + [ticker_context.upper()]))
        signal.entities   = entities
        signal.sector_tags = sectors

        # 3. Core sentiment scoring (source-specific)
        if source == "fed":
            raw_score, key_phrases = self.fed_analyser.analyse(text)
            signal.key_phrases = key_phrases
        elif source == "social":
            raw_score, key_phrases = self.social.analyse(text, engagement_score)
            signal.key_phrases = key_phrases
        else:
            # News / transcript — lexicon based
            raw_score, key_phrases = self.lexicon.score(tokens)
            signal.key_phrases = key_phrases

        # 4. Adjust and normalise
        signal.raw_score      = raw_score
        signal.adjusted_score = self._adjust(raw_score, signal.word_count, source)
        signal.confidence     = self._confidence(signal)
        signal.label          = self._label(signal.adjusted_score)

        return signal

    def batch_analyse(
        self,
        texts: List[str],
        source: str = "news",
        engagement_scores: Optional[List[float]] = None,
    ) -> List[SentimentSignal]:
        """Analyse a list of texts from the same source."""
        if engagement_scores is None:
            engagement_scores = [1.0] * len(texts)
        return [
            self.analyse(t, source=source, engagement_score=e)
            for t, e in zip(texts, engagement_scores)
        ]

    def summarise(
        self,
        signals: List[SentimentSignal],
        weights: Optional[Dict[str, float]] = None,
    ) -> MacroSentimentSummary:
        """
        Aggregate multiple signals into a MacroSentimentSummary.

        Default source weights: news=0.50, fed=0.30, social=0.20
        """
        default_w = {"news": 0.50, "fed": 0.30, "social": 0.20, "transcript": 0.40}
        w = weights or default_w

        summary = MacroSentimentSummary(n_documents=len(signals), signals=signals)

        if not signals:
            return summary

        # Group by source
        by_source: Dict[str, List[SentimentSignal]] = {}
        for sig in signals:
            by_source.setdefault(sig.source_type, []).append(sig)

        source_scores: Dict[str, float] = {}
        for src, sigs in by_source.items():
            # Confidence-weighted average
            total_conf = sum(s.confidence for s in sigs)
            if total_conf > 0:
                source_scores[src] = sum(
                    s.adjusted_score * s.confidence for s in sigs
                ) / total_conf
            else:
                source_scores[src] = 0.0

        summary.news_score   = source_scores.get("news", 0.0)
        summary.fed_score    = source_scores.get("fed", 0.0)
        summary.social_score = source_scores.get("social", 0.0)

        # Weighted overall
        total_w = sum(w.get(src, 0.25) for src in source_scores)
        if total_w > 0:
            summary.overall_score = sum(
                source_scores[src] * w.get(src, 0.25)
                for src in source_scores
            ) / total_w
        else:
            summary.overall_score = 0.0

        summary.overall_label     = self._label(summary.overall_score)
        summary.top_entities      = self._top_entities(signals)
        summary.top_themes        = self._top_themes(signals)
        summary.market_implication = self._implication(summary)

        return summary

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _adjust(raw: float, word_count: int, source: str) -> float:
        """Apply length and source dampening."""
        # Short texts are less reliable
        length_factor = min(1.0, math.log1p(word_count) / math.log1p(50))
        # Social is noisier → dampen
        source_dampen = {"fed": 1.0, "news": 0.9, "transcript": 0.95, "social": 0.7}.get(source, 0.85)
        return float(max(-1.0, min(1.0, raw * length_factor * source_dampen)))

    @staticmethod
    def _confidence(sig: SentimentSignal) -> float:
        """Confidence 0–1 based on text length and signal strength."""
        length_conf = min(1.0, sig.word_count / 50)
        signal_conf = min(1.0, abs(sig.raw_score) * 2)
        return round((length_conf + signal_conf) / 2, 3)

    @staticmethod
    def _label(score: float) -> str:
        if score >= 0.35:
            return "BULLISH"
        elif score >= 0.10:
            return "MILDLY_BULLISH"
        elif score <= -0.35:
            return "BEARISH"
        elif score <= -0.10:
            return "MILDLY_BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _top_entities(signals: List[SentimentSignal]) -> List[str]:
        count: Dict[str, int] = {}
        for sig in signals:
            for e in sig.entities:
                count[e] = count.get(e, 0) + 1
        return sorted(count, key=count.get, reverse=True)[:10]  # type: ignore[arg-type]

    @staticmethod
    def _top_themes(signals: List[SentimentSignal]) -> List[str]:
        count: Dict[str, int] = {}
        for sig in signals:
            for s in sig.sector_tags:
                count[s] = count.get(s, 0) + 1
        return sorted(count, key=count.get, reverse=True)[:5]  # type: ignore[arg-type]

    @staticmethod
    def _implication(summary: MacroSentimentSummary) -> str:
        score = summary.overall_score
        fed   = summary.fed_score
        label = summary.overall_label

        if fed <= -0.3:
            return "FED is hawkish → rates likely higher, risk-off environment"
        elif fed >= 0.3:
            return "FED is dovish → accommodative policy, risk-on tailwind"
        elif label == "BULLISH":
            return "Broad sentiment bullish → equities likely supported"
        elif label == "BEARISH":
            return "Broad sentiment bearish → defensive positioning recommended"
        return "Mixed signals → neutral stance, monitor for directional catalyst"
