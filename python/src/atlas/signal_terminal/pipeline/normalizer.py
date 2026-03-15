"""
Normalizer — converts RawItem → Signal with all fields populated.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime
from typing import List

from ..collectors.base import RawItem
from ..models import Signal


# Strip HTML tags for body cleanup
_HTML_RE = re.compile(r"<[^>]+>")

# Basic ticker pattern: 1–5 uppercase letters, possibly preceded by $ or followed by nothing
# We'll extract and validate in the matcher step; here we do rough extraction.
_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{2,5})(?!\w)")

# Cashtag-only (more reliable): $AAPL, $BTC
_CASHTAG_RE = re.compile(r"\$([A-Z]{1,5})\b")


def _clean_body(text: str) -> str:
    text = _HTML_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()[:2000]


def _hash(source_id: str, url: str, title: str) -> str:
    raw = f"{source_id}|{url}|{title[:120]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _extract_cashtags(text: str) -> List[str]:
    found = _CASHTAG_RE.findall(text)
    return list(dict.fromkeys(t.upper() for t in found if t))


class Normalizer:
    """Convert raw collector output into Signal objects."""

    def normalize(self, raw: RawItem) -> Signal:
        title = (raw.title or "").strip()
        body  = _clean_body(raw.body or "")
        url   = (raw.url or "").strip()

        pub = raw.published_at or datetime.utcnow()

        # Cashtag extraction from title + body
        combined = f"{title} {body}"
        tickers  = _extract_cashtags(combined)

        return Signal(
            source_id=raw.source_id,
            raw_id=raw.raw_id or "",
            url=url or None,
            title=title,
            body=body or None,
            author=raw.author or None,
            published_at=pub,
            collected_at=datetime.utcnow(),
            tickers=tickers,
            content_hash=_hash(raw.source_id, url, title),
            # category / sentiment / scoring filled by later pipeline stages
        )
