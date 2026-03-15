"""
AlertService — evaluates AlertRules against incoming Signals.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

from ..models import AlertRule, Match, Signal
from ..storage import SignalRepository

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, repo: SignalRepository):
        self._repo = repo

    def evaluate(self, sig: Signal, matches: List[Match]) -> List[AlertRule]:
        """Check all enabled rules against the signal. Fire any that match."""
        rules   = self._repo.get_alert_rules(enabled_only=True)
        fired   = []
        for rule in rules:
            if self._matches(rule, sig, matches):
                self._fire(rule, sig)
                fired.append(rule)
        return fired

    def _matches(self, rule: AlertRule, sig: Signal, matches: List[Match]) -> bool:
        cond = rule.conditions
        if not cond:
            return False   # empty condition = never fire

        # ticker condition
        if "ticker" in cond:
            allowed = cond["ticker"] if isinstance(cond["ticker"], list) else [cond["ticker"]]
            matched_tickers = {m.ticker for m in matches} | set(sig.tickers)
            if not any(t.upper() in matched_tickers for t in allowed):
                return False

        # category
        if "category" in cond:
            allowed = cond["category"] if isinstance(cond["category"], list) else [cond["category"]]
            if sig.category not in allowed:
                return False

        # sentiment
        if "sentiment" in cond:
            if sig.sentiment != cond["sentiment"]:
                return False

        # urgency
        if "urgency" in cond:
            _ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            if _ORDER.get(sig.urgency, 0) < _ORDER.get(cond["urgency"], 0):
                return False

        # relevance_min
        if "relevance_min" in cond:
            if sig.relevance_score < float(cond["relevance_min"]):
                return False

        # source_id
        if "source_id" in cond:
            allowed = cond["source_id"] if isinstance(cond["source_id"], list) else [cond["source_id"]]
            if sig.source_id not in allowed:
                return False

        # keywords_any
        if "keywords_any" in cond:
            kws = [k.lower() for k in cond["keywords_any"]]
            full = f"{sig.title} {sig.body or ''}".lower()
            if not any(k in full for k in kws):
                return False

        return True

    def _fire(self, rule: AlertRule, sig: Signal):
        details: Dict[str, Any] = {
            "signal_title": sig.title[:120],
            "category":     sig.category,
            "sentiment":    sig.sentiment,
            "urgency":      sig.urgency,
            "relevance":    sig.relevance_score,
            "tickers":      sig.tickers,
        }

        if rule.action == "log":
            logger.warning(
                "[ALERT] Rule=%r fired | %s | %s/%s | rel=%.2f | %s",
                rule.name, sig.tickers, sig.category, sig.sentiment,
                sig.relevance_score, sig.title[:80],
            )

        elif rule.action == "webhook":
            self._send_webhook(rule.action_config, sig, details)

        self._repo.record_alert_trigger(rule.id, sig.id, details)

    def _send_webhook(self, cfg: Dict[str, Any], sig: Signal, details: Dict[str, Any]):
        url = cfg.get("url", "")
        if not url:
            return
        try:
            import requests
            requests.post(url, json=details, timeout=8)
        except Exception as exc:
            logger.warning("[Alert] webhook POST failed to %s: %s", url, exc)
