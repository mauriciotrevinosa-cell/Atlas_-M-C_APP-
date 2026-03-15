"""
Signal Terminal — FastAPI router.
Mount with:  app.include_router(st_router, prefix="/api/signals")
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import AlertRule, Source, SourceType, WatchlistItem
from ..scheduler import get_scheduler
from .schemas import (
    AlertRuleCreate, AlertRuleOut, SignalListOut, SignalOut,
    SourceCreate, SourceOut, StatsOut,
    WatchlistAddRequest, WatchlistItemOut, WhaleEventOut,
)

logger  = logging.getLogger(__name__)
router  = APIRouter(tags=["signal_terminal"])


def _svc():
    sch = get_scheduler()
    if sch is None:
        raise HTTPException(503, "Signal Terminal not initialised — call /api/signals/start first")
    return sch.signal_svc, sch.watch_svc


# ── Stats ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsOut, summary="Signal Terminal statistics")
def get_stats():
    svc, _ = _svc()
    return StatsOut(**svc.get_stats())


# ── Signals ───────────────────────────────────────────────────────────────

@router.get("", response_model=SignalListOut, summary="Query the signal feed")
def list_signals(
    limit:     int            = Query(50, le=200),
    offset:    int            = Query(0, ge=0),
    ticker:    Optional[str]  = Query(None),
    category:  Optional[str]  = Query(None),
    sentiment: Optional[str]  = Query(None),
    source_id: Optional[str]  = Query(None),
    since:     Optional[str]  = Query(None, description="ISO datetime, e.g. 2024-01-01T00:00:00"),
):
    svc, _ = _svc()
    since_dt = datetime.fromisoformat(since) if since else None
    items = svc.query(
        limit=limit, offset=offset,
        ticker=ticker, category=category, sentiment=sentiment,
        source_id=source_id, since=since_dt,
    )
    return SignalListOut(
        items=[SignalOut(**s.dict()) for s in items],
        total=len(items),
        limit=limit,
        offset=offset,
    )


@router.get("/{signal_id}", response_model=SignalOut, summary="Get a single signal")
def get_signal(signal_id: str):
    svc, _ = _svc()
    sig = svc.get_signal(signal_id)
    if not sig:
        raise HTTPException(404, "Signal not found")
    return SignalOut(**sig.dict())


# ── Sources ───────────────────────────────────────────────────────────────

@router.get("/sources/list", response_model=List[SourceOut], summary="List configured sources")
def list_sources(enabled_only: bool = Query(True)):
    _, wsvc = _svc()
    return [SourceOut(**s.dict()) for s in wsvc.get_sources(enabled_only=enabled_only)]


@router.post("/sources", response_model=SourceOut, summary="Add a new source")
def add_source(body: SourceCreate):
    _, wsvc = _svc()
    src = Source(
        id=body.id, name=body.name, type=SourceType(body.type),
        url=body.url, enabled=body.enabled, refresh_interval=body.refresh_interval,
        config=body.config,
    )
    wsvc.add_source(src)
    return SourceOut(**src.dict())


@router.patch("/sources/{source_id}/toggle", response_model=SourceOut, summary="Enable / disable a source")
def toggle_source(source_id: str, enabled: bool = Query(...)):
    _, wsvc = _svc()
    src = wsvc.toggle_source(source_id, enabled)
    if not src:
        raise HTTPException(404, "Source not found")
    return SourceOut(**src.dict())


# ── Watchlist ─────────────────────────────────────────────────────────────

@router.get("/watchlist", response_model=List[WatchlistItemOut], summary="Get watchlist")
def get_watchlist():
    _, wsvc = _svc()
    return [WatchlistItemOut(**i.dict()) for i in wsvc.get_all()]


@router.post("/watchlist", response_model=WatchlistItemOut, summary="Add ticker to watchlist")
def add_to_watchlist(body: WatchlistAddRequest):
    _, wsvc = _svc()
    item = WatchlistItem(**body.dict())
    wsvc.add(item)
    return WatchlistItemOut(**item.dict())


@router.delete("/watchlist/{ticker}", summary="Remove ticker from watchlist")
def remove_from_watchlist(ticker: str):
    _, wsvc = _svc()
    ok = wsvc.remove(ticker)
    if not ok:
        raise HTTPException(404, f"Ticker {ticker.upper()} not in watchlist")
    return {"removed": ticker.upper()}


# ── Alert Rules ───────────────────────────────────────────────────────────

@router.get("/alerts/rules", response_model=List[AlertRuleOut], summary="List alert rules")
def list_alert_rules():
    svc, _ = _svc()
    rules = svc._repo.get_alert_rules(enabled_only=False)
    return [AlertRuleOut(**r.dict()) for r in rules]


@router.post("/alerts/rules", response_model=AlertRuleOut, summary="Create alert rule")
def create_alert_rule(body: AlertRuleCreate):
    svc, _ = _svc()
    rule = AlertRule(
        name=body.name, conditions=body.conditions,
        action=body.action, action_config=body.action_config,
    )
    svc._repo.upsert_alert_rule(rule)
    return AlertRuleOut(**rule.dict())


@router.patch("/alerts/rules/{rule_id}", response_model=AlertRuleOut, summary="Enable / disable an alert rule")
def toggle_alert_rule(rule_id: str, enabled: bool = Query(...)):
    svc, _ = _svc()
    rules = svc._repo.get_alert_rules(enabled_only=False)
    rule = next((r for r in rules if r.id == rule_id), None)
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    rule.enabled = enabled
    svc._repo.upsert_alert_rule(rule)
    return AlertRuleOut(**rule.dict())


@router.delete("/alerts/rules/{rule_id}", summary="Delete an alert rule")
def delete_alert_rule(rule_id: str):
    svc, _ = _svc()
    ok = svc._repo.delete_alert_rule(rule_id)
    if not ok:
        raise HTTPException(404, "Alert rule not found")
    return {"deleted": rule_id}


# ── Whale Events ──────────────────────────────────────────────────────────

@router.get("/whales", response_model=List[WhaleEventOut], summary="Recent whale events")
def get_whale_events(
    ticker: Optional[str] = Query(None),
    limit:  int           = Query(50, le=200),
    offset: int           = Query(0, ge=0),
):
    svc, _ = _svc()
    events = svc._repo.get_whale_events(ticker=ticker, limit=limit, offset=offset)
    return [WhaleEventOut(**e.dict()) for e in events]


# ── Scheduler control ─────────────────────────────────────────────────────

@router.post("/collect/now", summary="Trigger a manual collection run")
async def collect_now():
    sch = get_scheduler()
    if sch is None:
        raise HTTPException(503, "Signal Terminal not initialised")
    result = await sch.run_once()
    return result


@router.post("/start", summary="Start the background scheduler")
async def start_scheduler():
    sch = get_scheduler()
    if sch is None:
        raise HTTPException(503, "Signal Terminal not initialised")
    await sch.start()
    return {"status": "started"}


@router.post("/stop", summary="Stop the background scheduler")
async def stop_scheduler():
    sch = get_scheduler()
    if sch is None:
        raise HTTPException(503, "Signal Terminal not initialised")
    await sch.stop()
    return {"status": "stopped"}
