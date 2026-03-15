"""
AlertService — evaluates AlertRules against incoming Signals.

Supported actions:
  log       — writes to Python logger (always works)
  telegram  — sends message via Telegram Bot API
              requires TELEGRAM_BOT_TOKEN env var
              action_config: { "chat_id": "<chat or group id>" }
  discord   — posts an embed to a Discord webhook
              action_config: { "url": "<webhook url>" }
  webhook   — HTTP POST JSON to any URL
              action_config: { "url": "<url>" }
"""
from __future__ import annotations
import json
import logging
import os
import urllib.request
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

        # Always log
        logger.warning(
            "[ALERT] Rule=%r fired | %s | %s/%s | rel=%.2f | %s",
            rule.name, sig.tickers, sig.category, sig.sentiment,
            sig.relevance_score, sig.title[:80],
        )

        if rule.action == "telegram":
            self._send_telegram(rule.action_config, sig)
        elif rule.action == "discord":
            self._send_discord(rule.action_config, sig, details)
        elif rule.action == "webhook":
            self._send_webhook(rule.action_config, sig, details)

        self._repo.record_alert_trigger(rule.id, sig.id, details)

    # ── Notification senders ──────────────────────────────────────────────

    def _send_telegram(self, cfg: Dict[str, Any], sig: Signal):
        """Send a Telegram message via Bot API — no extra dependencies (urllib only)."""
        token   = cfg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = cfg.get("chat_id",  "") or os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            logger.warning("[Alert] Telegram: set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars")
            return

        sent_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(sig.sentiment, "")
        tickers   = " ".join(f"#{t}" for t in sig.tickers[:5]) if sig.tickers else ""
        text = (
            f"*[{sig.urgency.upper()}]* {sent_icon} *{sig.category}*\n"
            f"{sig.title[:200]}\n"
            f"{tickers}\n"
            f"relevance: {sig.relevance_score:.0%} · {sig.source_id}"
        )
        payload = json.dumps({
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": "Markdown",
        }).encode()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10):
                pass
            logger.info("[Alert] Telegram message sent to %s", chat_id)
        except Exception as exc:
            logger.warning("[Alert] Telegram send failed: %s", exc)

    def _send_discord(self, cfg: Dict[str, Any], sig: Signal, details: Dict[str, Any]):
        """Post a Discord embed via webhook URL."""
        url = cfg.get("url", "")
        if not url:
            logger.warning("[Alert] Discord: missing webhook url in action_config")
            return

        SENT_COLOR = {"bullish": 0x2ecc71, "bearish": 0xe74c3c, "neutral": 0x95a5a6}
        color      = SENT_COLOR.get(sig.sentiment, 0x7f8c8d)
        embed = {
            "title":       f"[{sig.urgency.upper()}] {sig.category} — {sig.sentiment}",
            "description": sig.title[:300],
            "color":       color,
            "fields": [
                {"name": "Tickers",    "value": ", ".join(sig.tickers[:8]) or "—", "inline": True},
                {"name": "Relevance",  "value": f"{sig.relevance_score:.0%}",       "inline": True},
                {"name": "Source",     "value": sig.source_id,                      "inline": True},
            ],
            "footer": {"text": "Atlas Signal Terminal"},
        }
        if sig.url:
            embed["url"] = sig.url

        payload = json.dumps({"embeds": [embed]}).encode()
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10):
                pass
            logger.info("[Alert] Discord embed sent")
        except Exception as exc:
            logger.warning("[Alert] Discord send failed: %s", exc)

    def _send_webhook(self, cfg: Dict[str, Any], sig: Signal, details: Dict[str, Any]):
        """HTTP POST JSON to an arbitrary URL."""
        url = cfg.get("url", "")
        if not url:
            return
        payload = json.dumps(details).encode()
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception as exc:
            logger.warning("[Alert] webhook POST failed to %s: %s", url, exc)
