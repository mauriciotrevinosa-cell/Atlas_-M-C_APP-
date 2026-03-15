"""
NitterCollector — Twitter/X signals via public Nitter RSS mirrors.

Nitter is an open-source Twitter front-end that exposes RSS without auth.
Multiple public instances rotate in case one is down.

Source config keys:
  query         : str   search query or @handle or $cashtag (used to pick endpoint)
  query_type    : str   "search" | "user" | "hashtag"  (default: "search")
  instance      : str   override Nitter instance URL  (optional)

No API key required. Falls back to next instance on error.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from .base import BaseCollector, RawItem
from .rss_collector import _parse_date
from ..models import Source

logger = logging.getLogger(__name__)

# Public Nitter instances — rotate on failure
_NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.cz",
    "https://nitter.mint.lgbt",
]

_RATE_LIMIT_S = 3.0
_last_nitter_call = 0.0

MAX_ITEMS = 40


def _rate_limit():
    global _last_nitter_call
    wait = _RATE_LIMIT_S - (time.time() - _last_nitter_call)
    if wait > 0:
        time.sleep(wait)
    _last_nitter_call = time.time()


class NitterCollector(BaseCollector):
    """Collect tweets matching a query or user timeline via Nitter RSS."""

    def fetch(self) -> List[RawItem]:
        cfg          = self.source.config
        query        = cfg.get("query", "")
        query_type   = cfg.get("query_type", "search")
        override_url = cfg.get("instance", "")

        if not query:
            logger.warning("[Nitter] no query configured for source %s", self.source_id)
            return []

        for instance in ([override_url] if override_url else _NITTER_INSTANCES):
            feed_url = self._build_url(instance, query, query_type)
            _rate_limit()
            items = self._try_fetch(feed_url)
            if items is not None:
                return items

        logger.warning("[Nitter] all instances failed for query=%r", query)
        return []

    def _build_url(self, instance: str, query: str, qtype: str) -> str:
        base = instance.rstrip("/")
        if qtype == "user":
            # @handle → /handle/rss
            handle = query.lstrip("@")
            return f"{base}/{handle}/rss"
        if qtype == "hashtag":
            tag = query.lstrip("#")
            return f"{base}/search/rss?q=%23{tag}&f=tweets"
        # Default: search (handles $AAPL, "Tesla earnings", etc.)
        import urllib.parse
        return f"{base}/search/rss?q={urllib.parse.quote(query)}&f=tweets"

    def _try_fetch(self, feed_url: str) -> Optional[List[RawItem]]:
        """Returns list on success, None on any error."""
        import urllib.request
        import xml.etree.ElementTree as ET

        headers = {"User-Agent": "AtlasSignalTerminal/1.0"}
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status != 200:
                    return None
                raw = resp.read()
        except Exception as exc:
            logger.debug("[Nitter] fetch error %s: %s", feed_url, exc)
            return None

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return None

        items: List[RawItem] = []
        for item in root.findall(".//item")[:MAX_ITEMS]:
            def _t(tag: str) -> str:
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            pub = _parse_date(_t("pubDate")) or datetime.utcnow()
            title = _t("title")
            link  = _t("link")
            desc  = _t("description")

            if not title:
                continue

            items.append(RawItem(
                source_id=self.source_id,
                raw_id=link,
                title=title,
                body=desc,
                url=link,
                author=_t("dc:creator") or _t("author") or "",
                published_at=pub,
                extra={"platform": "twitter", "instance": feed_url.split("/")[2]},
            ))

        logger.debug("[Nitter] fetched %d items from %s", len(items), feed_url)
        return items
