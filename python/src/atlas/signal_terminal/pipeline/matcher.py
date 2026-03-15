"""
Matcher — links signals to watchlist items.

Strategy:
  1. EXACT  — ticker symbol ($AAPL, uppercase word) found in title or body
  2. FUZZY  — company name / alias found in title (case-insensitive)
  3. KEYWORD — sector/tag overlap (future extension)

Returns List[Match] for each (signal, watchlist_item) pair.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import List

from ..models import Match, MatchType, Signal, WatchlistItem

# Matches $TICKER or standalone TICKER surrounded by word boundaries
_TICKER_RE = re.compile(r"(?:\$([A-Z]{1,5})\b)|(?<![A-Z])([A-Z]{2,5})(?![A-Z])")


def _tickers_in_text(text: str) -> List[str]:
    """Extract potential ticker symbols from text."""
    found = set()
    for m in _TICKER_RE.finditer(text):
        t = m.group(1) or m.group(2)
        if t:
            found.add(t.upper())
    return list(found)


class Matcher:
    def __init__(self, watchlist: List[WatchlistItem]):
        self._watchlist = watchlist

    def match(self, sig: Signal) -> List[Match]:
        combined = f"{sig.title} {sig.body or ''}".upper()
        text_tickers = set(_tickers_in_text(combined))
        # also use tickers already extracted by normalizer
        text_tickers.update(t.upper() for t in sig.tickers)

        matches: List[Match] = []
        seen_items = set()

        for item in self._watchlist:
            if item.id in seen_items:
                continue
            ticker = item.ticker.upper()

            # 1. Exact ticker match
            if ticker in text_tickers:
                matches.append(Match(
                    signal_id=sig.id,
                    watchlist_item_id=item.id,
                    ticker=ticker,
                    match_type=MatchType.EXACT,
                    match_score=1.0,
                    created_at=datetime.utcnow(),
                ))
                seen_items.add(item.id)
                continue

            # 2. Fuzzy — company name / alias
            lower_text = f"{sig.title} {sig.body or ''}".lower()
            candidates = [item.name or ""] + (item.aliases or [])
            for alias in candidates:
                alias = alias.strip().lower()
                if alias and len(alias) >= 3 and alias in lower_text:
                    matches.append(Match(
                        signal_id=sig.id,
                        watchlist_item_id=item.id,
                        ticker=ticker,
                        match_type=MatchType.FUZZY,
                        match_score=0.75,
                        created_at=datetime.utcnow(),
                    ))
                    seen_items.add(item.id)
                    break

        # Update sig.tickers to include all matched tickers
        all_matched = list({m.ticker for m in matches} | set(sig.tickers))
        sig.tickers = all_matched

        return matches
