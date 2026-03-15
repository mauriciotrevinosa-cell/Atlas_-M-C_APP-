"""
RedditCollector — ingests subreddit posts via the public JSON API (no auth).

Source config keys (all optional):
  subreddit  : str   e.g. "stocks"
  sort       : str   "new" | "hot" | "top" | "rising"  (default: "new")
  limit      : int   max posts per fetch                (default: 25)
  time_filter: str   "hour"|"day"|"week" — only relevant for sort=top
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from typing import List

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from .base import BaseCollector, RawItem
from ..models import Source

logger = logging.getLogger(__name__)

_REDDIT_BASE   = "https://www.reddit.com"
_USER_AGENT    = "AtlasSignalTerminal/1.0 (educational; contact dev@atlas.local)"
_RATE_LIMIT_S  = 2.0        # seconds between requests (Reddit ToS: ≤ 1 req/s)
_last_call_ts  = 0.0


def _rate_limit():
    global _last_call_ts
    wait = _RATE_LIMIT_S - (time.time() - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


class RedditCollector(BaseCollector):
    """Collect posts from a public subreddit."""

    def fetch(self) -> List[RawItem]:
        cfg = self.source.config
        subreddit = cfg.get("subreddit") or self.source.url.rstrip("/").split("/")[-1]
        sort      = cfg.get("sort", "new")
        limit     = int(cfg.get("limit", 25))

        if not subreddit:
            logger.warning("[Reddit] no subreddit configured for source %s", self.source_id)
            return []

        url = f"{_REDDIT_BASE}/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"
        if sort == "top":
            t = cfg.get("time_filter", "day")
            url += f"&t={t}"

        _rate_limit()

        if not _REQUESTS_OK:
            return self._fetch_urllib(url, subreddit)
        try:
            resp = _requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
            resp.raise_for_status()
            return self._parse_listing(resp.json(), subreddit)
        except Exception as exc:
            logger.warning("[Reddit] requests failed for r/%s: %s — trying urllib", subreddit, exc)
            return self._fetch_urllib(url, subreddit)

    def _fetch_urllib(self, url: str, subreddit: str) -> List[RawItem]:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return self._parse_listing(data, subreddit)
        except Exception as exc:
            logger.error("[Reddit] urllib failed for r/%s: %s", subreddit, exc)
            return []

    def _parse_listing(self, data: dict, subreddit: str) -> List[RawItem]:
        posts = data.get("data", {}).get("children", [])
        items: List[RawItem] = []
        for post in posts:
            d = post.get("data", {})
            if d.get("is_self") is False and not d.get("selftext"):
                # link post — title + URL only
                body = ""
            else:
                body = (d.get("selftext") or "").strip()

            created_utc = d.get("created_utc")
            pub = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc).replace(tzinfo=None)
                if created_utc else datetime.utcnow()
            )

            items.append(RawItem(
                source_id=self.source_id,
                raw_id=d.get("id", ""),
                title=(d.get("title") or "").strip(),
                body=body,
                url=f"{_REDDIT_BASE}{d.get('permalink', '')}",
                author=d.get("author", "") or "",
                published_at=pub,
                extra={
                    "score":      d.get("score", 0),
                    "upvote_ratio": d.get("upvote_ratio", 0.5),
                    "num_comments": d.get("num_comments", 0),
                    "flair":      d.get("link_flair_text") or "",
                    "subreddit":  subreddit,
                },
            ))
        return items
