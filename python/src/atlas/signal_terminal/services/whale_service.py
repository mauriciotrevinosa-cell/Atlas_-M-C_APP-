"""
WhaleService — detect large/unusual activity from signals and store WhaleEvents.

Detection heuristics (keyword + pattern based):
  • "unusual options" / "dark pool" / "block trade" → UNUSUAL_OPTIONS / DARK_POOL / BLOCK_TRADE
  • dollar amounts: $Xm / $Xb / $X million / $X billion → size extraction
  • SEC Form 4 / insider → INSIDER
  • short squeeze → SHORT_SQUEEZE
"""
from __future__ import annotations
import logging
import re
from typing import List, Optional

from ..models import Signal, SignalCategory, WhaleEvent, WhaleEventType
from ..storage import SignalRepository
from .. import config as cfg

logger = logging.getLogger(__name__)

# Dollar amount patterns: $50M, $1.2B, $500 million, $1.5 billion
_DOLLAR_RE = re.compile(
    r"\$\s*(\d+(?:\.\d+)?)\s*(m|b|million|billion|k|thousand)\b",
    re.IGNORECASE,
)

_WHALE_TRIGGERS = [
    # (pattern_in_lower_text, WhaleEventType)
    (re.compile(r"unusual.{0,10}option"),   WhaleEventType.UNUSUAL_OPTIONS),
    (re.compile(r"dark.{0,5}pool"),         WhaleEventType.DARK_POOL),
    (re.compile(r"block.{0,5}trade"),       WhaleEventType.BLOCK_TRADE),
    (re.compile(r"form\s*4|insider.{0,15}(buy|sell|purchase|transact)"),
                                            WhaleEventType.INSIDER),
    (re.compile(r"short.{0,10}squeeze"),    WhaleEventType.SHORT_SQUEEZE),
    (re.compile(r"large.{0,15}(buy|purchase|position|stake)"),
                                            WhaleEventType.LARGE_BUY),
    (re.compile(r"large.{0,15}(sell|dump|liquidat)"),
                                            WhaleEventType.LARGE_SELL),
]


def _extract_size(text: str) -> Optional[float]:
    for m in _DOLLAR_RE.finditer(text):
        num = float(m.group(1))
        unit = m.group(2).lower()
        if unit in ("b", "billion"):
            num *= 1_000_000_000
        elif unit in ("m", "million"):
            num *= 1_000_000
        elif unit in ("k", "thousand"):
            num *= 1_000
        if num >= cfg.WHALE_SIZE_THRESHOLDS["micro"]:
            return num
    return None


class WhaleService:
    def __init__(self, repo: SignalRepository):
        self._repo = repo

    def detect(self, sig: Signal) -> List[WhaleEvent]:
        """
        Check if the signal describes whale activity. If so, store a WhaleEvent.
        Returns list of events created.
        """
        # Only check whale-category signals or ones that mention size
        text = f"{sig.title} {sig.body or ''}".lower()
        events: List[WhaleEvent] = []

        detected_type: Optional[WhaleEventType] = None
        if sig.category == SignalCategory.WHALE:
            detected_type = WhaleEventType.UNKNOWN

        for pattern, evt_type in _WHALE_TRIGGERS:
            if pattern.search(text):
                detected_type = evt_type
                break

        if detected_type is None:
            return []

        size = _extract_size(text)

        for ticker in (sig.tickers or ["UNKNOWN"]):
            evt = WhaleEvent(
                signal_id=sig.id,
                ticker=ticker.upper(),
                event_type=detected_type,
                size=size,
                description=sig.title[:200],
                source=sig.source_id,
                confidence=min(0.5 + sig.relevance_score * 0.5, 1.0),
            )
            try:
                self._repo.insert_whale_event(evt)
                events.append(evt)
                logger.info("[Whale] %s %s ticker=%s size=%s", evt.event_type, evt.size_label, ticker, size)
            except Exception as exc:
                logger.warning("[Whale] insert error: %s", exc)

        return events
