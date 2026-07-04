"""
MarketIntelAgent - turns market signals into an Atlas intelligence brief.

This is an Atlas-native rebuild inspired by intake repos that describe market
intel, whale, funding, liquidation and sentiment agents. It does not execute
trades and does not copy external repo code.

Input (via AgentTask.inputs):
  signals: list of signal dicts from Signal Terminal or API feeds
  whale_events: list of whale/liquidation/unusual-flow event dicts
  market_snapshot: dict keyed by ticker/symbol with numeric market fields
  watchlist: optional list of symbols to prioritize

Output:
  market_brief, priority_assets, risk_flags, catalyst_map,
  suggested_agent_tasks, data_gaps, summary
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List

from .base import BaseAgent
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


class MarketIntelAgent(BaseAgent):
    """Builds a deterministic, read-only market intelligence report."""

    name: str = "market_intel_agent"
    version: str = "v1"

    REQUIRED_OUTPUT_KEYS = [
        "market_brief",
        "priority_assets",
        "risk_flags",
        "catalyst_map",
        "suggested_agent_tasks",
        "data_gaps",
        "summary",
    ]

    def run(self, task: AgentTask) -> AgentResult:
        signals = _as_list(task.inputs.get("signals"))
        whale_events = _as_list(task.inputs.get("whale_events"))
        market_snapshot = task.inputs.get("market_snapshot") or {}
        watchlist = {
            str(symbol).upper()
            for symbol in _as_list(task.inputs.get("watchlist"))
            if str(symbol).strip()
        }

        assets = self._score_assets(signals, whale_events, market_snapshot, watchlist)
        priority_assets = [asset for asset in assets if asset["intel_score"] > 0][:10]
        risk_flags = self._build_risk_flags(priority_assets, whale_events, market_snapshot)
        catalyst_map = self._build_catalyst_map(signals, whale_events)
        data_gaps = self._build_data_gaps(signals, whale_events, market_snapshot)
        suggested_tasks = self._suggest_tasks(priority_assets, risk_flags, data_gaps)
        brief = self._brief(priority_assets, risk_flags)

        summary = (
            f"Market intelligence brief generated for {len(priority_assets)} priority assets."
            if priority_assets
            else "Market intelligence brief generated with no priority assets."
        )

        result = {
            "market_brief": brief,
            "priority_assets": priority_assets,
            "risk_flags": risk_flags,
            "catalyst_map": catalyst_map,
            "suggested_agent_tasks": suggested_tasks,
            "data_gaps": data_gaps,
            "summary": summary,
        }

        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary=summary,
            result=result,
            metadata={
                "agent": self.name,
                "version": self.version,
                "signals_count": len(signals),
                "whale_events_count": len(whale_events),
                "snapshot_assets_count": len(market_snapshot),
                "mode": "read_only",
            },
        )

    def _score_assets(
        self,
        signals: List[Dict[str, Any]],
        whale_events: List[Dict[str, Any]],
        market_snapshot: Dict[str, Any],
        watchlist: set[str],
    ) -> List[Dict[str, Any]]:
        buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "symbol": "",
                "intel_score": 0.0,
                "sentiment_score": 0.0,
                "signal_count": 0,
                "whale_event_count": 0,
                "drivers": [],
                "risk_notes": [],
            }
        )

        for signal in signals:
            for symbol in _symbols_from_signal(signal):
                row = buckets[symbol]
                row["symbol"] = symbol
                row["signal_count"] += 1
                relevance = _float(signal.get("relevance_score"), 0.35)
                sentiment = _float(signal.get("sentiment_score"), 0.0)
                category = str(signal.get("category", "")).lower()
                category_boost = 0.15 if category in {"whale", "macro", "earnings"} else 0.05
                row["intel_score"] += relevance * 0.45 + abs(sentiment) * 0.20 + category_boost
                row["sentiment_score"] += sentiment
                title = str(signal.get("title") or signal.get("summary") or "signal").strip()
                if title and len(row["drivers"]) < 5:
                    row["drivers"].append(title[:140])

        for event in whale_events:
            symbol = str(event.get("ticker") or event.get("symbol") or "").upper().strip()
            if not symbol:
                continue
            row = buckets[symbol]
            row["symbol"] = symbol
            row["whale_event_count"] += 1
            size = _float(event.get("size"), 0.0)
            confidence = _float(event.get("confidence"), 0.5)
            event_type = str(event.get("event_type", "whale_event")).lower()
            row["intel_score"] += 0.25 + min(size / 100_000_000, 0.5) + confidence * 0.25
            row["risk_notes"].append(f"{event_type}: {_compact_money(size)}")

        for raw_symbol, raw_snapshot in market_snapshot.items():
            symbol = str(raw_symbol).upper().strip()
            if not symbol:
                continue
            snapshot = raw_snapshot or {}
            row = buckets[symbol]
            row["symbol"] = symbol
            volume_ratio = _float(snapshot.get("volume_ratio"), 1.0)
            oi_change = _float(snapshot.get("open_interest_change_pct"), 0.0)
            funding = _float(snapshot.get("funding_rate"), 0.0)
            liquidations = _float(snapshot.get("liquidation_usd"), 0.0)
            row["intel_score"] += min(max(volume_ratio - 1.0, 0.0), 3.0) * 0.10
            row["intel_score"] += min(abs(oi_change) / 20.0, 0.30)
            row["intel_score"] += min(abs(funding) * 12.0, 0.30)
            row["intel_score"] += min(liquidations / 50_000_000, 0.35)
            if volume_ratio >= 2.0:
                row["risk_notes"].append(f"volume_ratio={volume_ratio:.2f}")
            if abs(funding) >= 0.03:
                row["risk_notes"].append(f"funding_rate={funding:.3f}")
            if liquidations >= 5_000_000:
                row["risk_notes"].append(f"liquidations={_compact_money(liquidations)}")

        for symbol in watchlist:
            row = buckets[symbol]
            row["symbol"] = symbol
            row["intel_score"] += 0.10
            row["drivers"].append("watchlist priority")

        rows = []
        for row in buckets.values():
            count = max(row["signal_count"], 1)
            row["sentiment_score"] = round(row["sentiment_score"] / count, 4)
            row["intel_score"] = round(min(row["intel_score"], 1.0), 4)
            row["attention_level"] = _attention(row["intel_score"])
            rows.append(row)

        rows.sort(key=lambda item: (item["intel_score"], item["whale_event_count"]), reverse=True)
        return rows

    @staticmethod
    def _build_risk_flags(
        priority_assets: List[Dict[str, Any]],
        whale_events: List[Dict[str, Any]],
        market_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        flags: List[Dict[str, Any]] = []
        for asset in priority_assets:
            if asset["attention_level"] in {"high", "critical"} and asset["risk_notes"]:
                flags.append({
                    "symbol": asset["symbol"],
                    "severity": asset["attention_level"],
                    "reason": "; ".join(asset["risk_notes"][:3]),
                })

        for event in whale_events:
            event_type = str(event.get("event_type", "")).lower()
            size = _float(event.get("size"), 0.0)
            if event_type in {"large_sell", "liquidation", "dark_pool"} or size >= 50_000_000:
                flags.append({
                    "symbol": str(event.get("ticker") or event.get("symbol") or "UNKNOWN").upper(),
                    "severity": "high" if size < 100_000_000 else "critical",
                    "reason": f"{event_type or 'whale_event'} size {_compact_money(size)}",
                })

        for symbol, snapshot in market_snapshot.items():
            funding = _float((snapshot or {}).get("funding_rate"), 0.0)
            oi_change = _float((snapshot or {}).get("open_interest_change_pct"), 0.0)
            if abs(funding) >= 0.05 and abs(oi_change) >= 15:
                flags.append({
                    "symbol": str(symbol).upper(),
                    "severity": "high",
                    "reason": f"crowded derivatives: funding={funding:.3f}, oi_change={oi_change:.1f}%",
                })

        return flags[:12]

    @staticmethod
    def _build_catalyst_map(
        signals: List[Dict[str, Any]],
        whale_events: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        catalysts: Dict[str, List[str]] = defaultdict(list)
        for signal in signals:
            title = str(signal.get("title") or signal.get("summary") or "").strip()
            if not title:
                continue
            for symbol in _symbols_from_signal(signal):
                if len(catalysts[symbol]) < 5:
                    catalysts[symbol].append(title[:140])
        for event in whale_events:
            symbol = str(event.get("ticker") or event.get("symbol") or "").upper().strip()
            if symbol and len(catalysts[symbol]) < 5:
                event_type = str(event.get("event_type", "whale_event"))
                catalysts[symbol].append(f"{event_type} {_compact_money(_float(event.get('size'), 0.0))}")
        return dict(sorted(catalysts.items()))

    @staticmethod
    def _build_data_gaps(
        signals: List[Dict[str, Any]],
        whale_events: List[Dict[str, Any]],
        market_snapshot: Dict[str, Any],
    ) -> List[str]:
        gaps = []
        if not signals:
            gaps.append("No Signal Terminal signals were supplied.")
        if not whale_events:
            gaps.append("No whale/liquidation/unusual-flow events were supplied.")
        if not market_snapshot:
            gaps.append("No market snapshot was supplied.")
        if market_snapshot and all("funding_rate" not in (snap or {}) for snap in market_snapshot.values()):
            gaps.append("Funding-rate context is missing from the market snapshot.")
        if market_snapshot and all("open_interest_change_pct" not in (snap or {}) for snap in market_snapshot.values()):
            gaps.append("Open-interest change context is missing from the market snapshot.")
        return gaps

    @staticmethod
    def _suggest_tasks(
        priority_assets: List[Dict[str, Any]],
        risk_flags: List[Dict[str, Any]],
        data_gaps: List[str],
    ) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for asset in priority_assets[:3]:
            tasks.append({
                "agent_name": "repo_scout_agent",
                "objective": f"Research current catalyst context for {asset['symbol']}",
                "risk_level": "low",
            })
        if risk_flags:
            tasks.append({
                "agent_name": "reviewer_agent",
                "objective": "Review high-severity market risk flags before any strategy change",
                "risk_level": "medium",
            })
        if data_gaps:
            tasks.append({
                "agent_name": "ingestion_agent",
                "objective": "Ingest missing market intelligence feeds into Signal Terminal",
                "risk_level": "low",
            })
        return tasks[:6]

    @staticmethod
    def _brief(priority_assets: List[Dict[str, Any]], risk_flags: List[Dict[str, Any]]) -> str:
        if not priority_assets:
            return "No priority assets detected from the supplied market intelligence inputs."
        leaders = ", ".join(asset["symbol"] for asset in priority_assets[:5])
        risk_text = f"{len(risk_flags)} risk flags require review" if risk_flags else "no high-severity flags"
        return f"Top attention assets: {leaders}. {risk_text}. Read-only analysis; no trade execution."


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _symbols_from_signal(signal: Dict[str, Any]) -> Iterable[str]:
    raw = signal.get("tickers") or signal.get("symbols") or signal.get("ticker") or signal.get("symbol") or []
    for item in _as_list(raw):
        symbol = str(item).upper().strip()
        if symbol:
            yield symbol


def _float(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _compact_money(value: float) -> str:
    value = float(value or 0.0)
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


def _attention(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"
