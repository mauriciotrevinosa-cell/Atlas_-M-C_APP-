"""
MarketEventService - converts market microstructure snapshots into signals.

This is the Signal Terminal integration point for ideas like funding, open
interest, liquidation and unusual-volume scanners. It deliberately feeds the
existing SignalService pipeline instead of creating a second signal engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

from ..collectors.base import RawItem
from .signal_service import SignalService


DEFAULT_THRESHOLDS: Dict[str, float] = {
    "abs_funding_rate": 0.03,
    "abs_open_interest_change_pct": 12.0,
    "liquidation_usd": 5_000_000.0,
    "volume_ratio": 2.0,
}


class MarketEventService:
    """Builds Signal Terminal raw items from structured market snapshots."""

    source_id = "market_microstructure"

    def __init__(
        self,
        signal_service: SignalService,
        thresholds: Dict[str, float] | None = None,
    ):
        self._signal_service = signal_service
        self._thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self._thresholds.update(thresholds)

    def ingest_snapshots(self, snapshots: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """Convert snapshots to raw items and ingest them through SignalService."""
        raw_items = self.build_raw_items(snapshots)
        inserted, dupes = self._signal_service.ingest(raw_items)
        return {
            "raw_items": len(raw_items),
            "inserted": inserted,
            "duplicates": dupes,
        }

    def build_raw_items(self, snapshots: Iterable[Dict[str, Any]]) -> List[RawItem]:
        raw_items: List[RawItem] = []
        for snapshot in snapshots:
            symbol = str(snapshot.get("symbol") or snapshot.get("ticker") or "").upper().strip()
            if not symbol:
                continue
            observed_at = _parse_dt(snapshot.get("observed_at"))
            for event_type, title, body in self._events_for_snapshot(symbol, snapshot):
                raw_items.append(
                    RawItem(
                        source_id=self.source_id,
                        raw_id=_raw_id(symbol, event_type, observed_at),
                        title=title,
                        body=body,
                        author="atlas-market-event-service",
                        published_at=observed_at,
                        extra={"snapshot": snapshot, "event_type": event_type},
                    )
                )
        return raw_items

    def _events_for_snapshot(
        self,
        symbol: str,
        snapshot: Dict[str, Any],
    ) -> List[Tuple[str, str, str]]:
        events: List[Tuple[str, str, str]] = []
        funding = _float(snapshot.get("funding_rate"))
        oi_change = _float(snapshot.get("open_interest_change_pct"))
        liquidation = _float(snapshot.get("liquidation_usd"))
        volume_ratio = _float(snapshot.get("volume_ratio"))
        exchange = str(snapshot.get("exchange") or "market").strip()
        timeframe = str(snapshot.get("timeframe") or "latest").strip()

        if funding is not None and abs(funding) >= self._thresholds["abs_funding_rate"]:
            side = "positive" if funding > 0 else "negative"
            sentiment = "bearish risk" if funding > 0 else "short squeeze risk"
            events.append((
                "funding_extreme",
                f"${symbol} {side} funding rate extreme",
                (
                    f"${symbol} funding rate reached {funding:.4f} on {exchange} "
                    f"({timeframe}); crowded derivatives {sentiment}."
                ),
            ))

        if oi_change is not None and abs(oi_change) >= self._thresholds["abs_open_interest_change_pct"]:
            direction = "surge" if oi_change > 0 else "drop"
            events.append((
                "open_interest_shift",
                f"${symbol} open interest {direction} detected",
                (
                    f"${symbol} open interest change is {oi_change:.1f}% on {exchange} "
                    f"({timeframe}); whale positioning and leverage risk elevated."
                ),
            ))

        if liquidation is not None and liquidation >= self._thresholds["liquidation_usd"]:
            events.append((
                "liquidation_spike",
                f"${symbol} liquidation spike detected",
                (
                    f"${symbol} saw ${liquidation / 1_000_000:.1f} million liquidations "
                    f"on {exchange} ({timeframe}); liquidation cascade risk is elevated."
                ),
            ))

        if volume_ratio is not None and volume_ratio >= self._thresholds["volume_ratio"]:
            events.append((
                "volume_spike",
                f"${symbol} unusual volume spike detected",
                (
                    f"${symbol} volume ratio is {volume_ratio:.2f}x normal on {exchange} "
                    f"({timeframe}); unusual market activity requires review."
                ),
            ))

        return events


def _float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _raw_id(symbol: str, event_type: str, observed_at: datetime) -> str:
    stamp = observed_at.replace(microsecond=0).isoformat()
    return f"{symbol}:{event_type}:{stamp}"
