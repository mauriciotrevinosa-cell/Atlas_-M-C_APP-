"""
SECEdgarCollector — Form 4 / 8-K filings via SEC EDGAR RSS.

EDGAR publishes public RSS feeds for filings:
  • Form 4   — insider transactions (buy/sell by officers/directors)
  • Form 8-K — material events (earnings, M&A, guidance)
  • Form 13F — institutional holdings (quarterly)

No API key required. Rate limit: EDGAR requests max 10/second.
We stay well below that (1 per source per run).

Source config keys:
  form_type   : str    "4" | "8-K" | "13F"  (default: "4")
  company_cik : str    CIK number to filter by company (optional)
  count       : int    max items per fetch (default: 20, max 40)

RSS base: https://www.sec.gov/cgi-bin/browse-edgar
"""
from __future__ import annotations
import logging
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional

from .base import BaseCollector, RawItem
from .rss_collector import _parse_date
from ..models import Source

logger = logging.getLogger(__name__)

_EDGAR_BASE   = "https://www.sec.gov/cgi-bin/browse-edgar"
_USER_AGENT   = "AtlasSignalTerminal/1.0 dev@atlas.local"  # EDGAR requires a real contact
_RATE_LIMIT_S = 2.0
_last_call_ts = 0.0
MAX_ITEMS     = 40


def _rate_limit():
    global _last_call_ts
    wait = _RATE_LIMIT_S - (time.time() - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


def _edgar_rss_url(form_type: str, cik: Optional[str], count: int) -> str:
    params: dict = {
        "action":  "getcurrent",
        "type":    form_type,
        "dateb":   "",
        "owner":   "include",
        "count":   str(min(count, MAX_ITEMS)),
        "search_text": "",
        "output":  "atom",
    }
    if cik:
        params["CIK"] = cik
    return f"{_EDGAR_BASE}?{urllib.parse.urlencode(params)}"


class SECEdgarCollector(BaseCollector):
    """Ingest SEC EDGAR filings (Form 4, 8-K, 13F) as signals."""

    def fetch(self) -> List[RawItem]:
        cfg       = self.source.config
        form_type = cfg.get("form_type", "4")
        cik       = cfg.get("company_cik") or None
        count     = int(cfg.get("count", 20))

        url = _edgar_rss_url(form_type, cik, count)
        _rate_limit()

        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
        except Exception as exc:
            logger.error("[EDGAR] fetch failed: %s", exc)
            return []

        return self._parse_atom(raw, form_type)

    def _parse_atom(self, xml_bytes: bytes, form_type: str) -> List[RawItem]:
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            logger.error("[EDGAR] XML parse error: %s", exc)
            return []

        ns   = {"a": "http://www.w3.org/2005/Atom"}
        items: List[RawItem] = []

        for entry in root.findall("a:entry", ns)[:MAX_ITEMS]:
            def _t(tag: str) -> str:
                el = entry.find(f"a:{tag}", ns)
                return (el.text or "").strip() if el is not None else ""

            title   = _t("title")
            link_el = entry.find("a:link", ns)
            link    = link_el.get("href", "") if link_el is not None else ""
            summary = _t("summary")
            updated = _parse_date(_t("updated")) or datetime.utcnow()

            # Extract filer info from title: "form 4 - COMPANY NAME (CIK)"
            author = ""
            name_el = entry.find("a:author/a:name", ns)
            if name_el is not None:
                author = (name_el.text or "").strip()

            if not title:
                continue

            items.append(RawItem(
                source_id=self.source_id,
                raw_id=_t("id") or link,
                title=f"[SEC {form_type}] {title}",
                body=summary,
                url=link,
                author=author,
                published_at=updated,
                extra={"form_type": form_type, "sec_source": True},
            ))

        logger.debug("[EDGAR] parsed %d Form %s entries", len(items), form_type)
        return items
