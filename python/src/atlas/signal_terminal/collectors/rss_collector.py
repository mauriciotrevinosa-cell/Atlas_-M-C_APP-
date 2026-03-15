"""
RSSCollector — ingests RSS/Atom feeds.

Requires either:
  • feedparser  (pip install feedparser)  — preferred, handles edge cases well
  • stdlib xml.etree.ElementTree          — fallback, handles basic RSS 2.0

Source config keys:
  (none required — url comes from Source.url)
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import List, Optional

from .base import BaseCollector, RawItem
from ..models import Source

logger = logging.getLogger(__name__)


def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    """Try multiple date formats used across RSS feeds."""
    if not raw:
        return None
    import email.utils
    try:
        t = email.utils.parsedate_to_datetime(raw)
        return t.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt[:len(raw)])
        except Exception:
            pass
    return None


class RSSCollector(BaseCollector):
    """Collect signals from any RSS/Atom feed URL."""

    MAX_ITEMS = 50

    def fetch(self) -> List[RawItem]:
        url = self.source.url
        if not url:
            return []
        try:
            return self._fetch_feedparser(url)
        except ImportError:
            logger.debug("[RSS] feedparser not installed — using stdlib fallback")
            return self._fetch_stdlib(url)
        except Exception as exc:
            logger.warning("[RSS] feedparser error on %s: %s", url, exc)
            return self._fetch_stdlib(url)

    def _fetch_feedparser(self, url: str) -> List[RawItem]:
        import feedparser  # noqa: PLC0415
        feed = feedparser.parse(url)
        items: List[RawItem] = []
        for entry in feed.entries[:self.MAX_ITEMS]:
            pub = _parse_date(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            )
            items.append(RawItem(
                source_id=self.source_id,
                raw_id=getattr(entry, "id", "") or getattr(entry, "link", ""),
                title=(getattr(entry, "title", "") or "").strip(),
                body=(getattr(entry, "summary", "") or "").strip(),
                url=getattr(entry, "link", "") or "",
                author=getattr(entry, "author", "") or "",
                published_at=pub or datetime.utcnow(),
            ))
        return items

    def _fetch_stdlib(self, url: str) -> List[RawItem]:
        """Basic RSS 2.0 parser using only stdlib."""
        import xml.etree.ElementTree as ET
        import urllib.request

        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                xml_bytes = resp.read()
        except Exception as exc:
            logger.error("[RSS] stdlib fetch failed for %s: %s", url, exc)
            return []

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            logger.error("[RSS] XML parse error for %s: %s", url, exc)
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items: List[RawItem] = []

        # RSS 2.0
        for item in root.findall(".//item")[:self.MAX_ITEMS]:
            def _t(tag: str) -> str:
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            items.append(RawItem(
                source_id=self.source_id,
                raw_id=_t("guid") or _t("link"),
                title=_t("title"),
                body=_t("description"),
                url=_t("link"),
                author=_t("author") or _t("dc:creator"),
                published_at=_parse_date(_t("pubDate")) or datetime.utcnow(),
            ))

        if not items:
            # Atom
            for entry in root.findall(".//atom:entry", ns)[:self.MAX_ITEMS]:
                def _at(tag: str) -> str:
                    el = entry.find(f"atom:{tag}", ns)
                    return (el.text or "").strip() if el is not None else ""

                pub = _parse_date(_at("published") or _at("updated"))
                link_el = entry.find("atom:link", ns)
                url_val = link_el.get("href", "") if link_el is not None else ""
                items.append(RawItem(
                    source_id=self.source_id,
                    raw_id=_at("id"),
                    title=_at("title"),
                    body=_at("summary") or _at("content"),
                    url=url_val,
                    author=_at("name"),
                    published_at=pub or datetime.utcnow(),
                ))

        return items
