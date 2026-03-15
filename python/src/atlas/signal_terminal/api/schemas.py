"""
API request / response schemas for the Signal Terminal endpoints.
Separate from domain models so we can evolve the API contract independently.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Signals ───────────────────────────────────────────────────────────────

class SignalOut(BaseModel):
    id:              str
    source_id:       str
    url:             Optional[str]
    title:           str
    body:            Optional[str] = None
    author:          Optional[str]
    published_at:    datetime
    collected_at:    datetime
    category:        str
    sentiment:       str
    sentiment_score: float
    tickers:         List[str]
    keywords:        List[str]
    tags:            List[str]
    relevance_score: float
    urgency:         str


class SignalListOut(BaseModel):
    items:   List[SignalOut]
    total:   int
    limit:   int
    offset:  int


# ── Sources ───────────────────────────────────────────────────────────────

class SourceOut(BaseModel):
    id:               str
    name:             str
    type:             str
    url:              str
    enabled:          bool
    refresh_interval: int
    last_fetched_at:  Optional[datetime]
    last_error:       Optional[str]
    error_count:      int
    total_fetched:    int


class SourceCreate(BaseModel):
    id:               str
    name:             str
    type:             str       # "rss" | "reddit"
    url:              str       = ""
    enabled:          bool      = True
    refresh_interval: int       = 300
    config:           Dict[str, Any] = {}


# ── Watchlist ─────────────────────────────────────────────────────────────

class WatchlistItemOut(BaseModel):
    id:            str
    ticker:        str
    name:          Optional[str]
    asset_type:    str
    priority:      str
    tags:          List[str]
    aliases:       List[str]
    alert_enabled: bool
    added_at:      datetime


class WatchlistAddRequest(BaseModel):
    ticker:        str
    name:          Optional[str] = None
    asset_type:    str           = "stock"
    priority:      str           = "medium"
    tags:          List[str]     = []
    aliases:       List[str]     = []
    notes:         Optional[str] = None
    alert_enabled: bool          = True


# ── Alert Rules ───────────────────────────────────────────────────────────

class AlertRuleOut(BaseModel):
    id:                str
    name:              str
    enabled:           bool
    conditions:        Dict[str, Any]
    action:            str
    action_config:     Dict[str, Any]
    created_at:        datetime
    last_triggered_at: Optional[datetime]
    trigger_count:     int


class AlertRuleCreate(BaseModel):
    name:          str
    conditions:    Dict[str, Any]
    action:        str            = "log"
    action_config: Dict[str, Any] = {}


# ── Whale Events ──────────────────────────────────────────────────────────

class WhaleEventOut(BaseModel):
    id:          str
    signal_id:   Optional[str]
    ticker:      str
    event_type:  str
    size:        Optional[float]
    size_label:  str
    description: str
    confidence:  float
    detected_at: datetime


# ── Stats ─────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total_signals:   int
    recent_24h:      int
    active_sources:  int
    watchlist_items: int
    whale_events:    int
    alert_triggers:  int
