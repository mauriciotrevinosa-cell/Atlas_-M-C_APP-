"""
Source — a data source configuration record.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid


class SourceType(str, Enum):
    RSS     = "rss"
    REDDIT  = "reddit"
    NITTER  = "nitter"    # Twitter/X via Nitter RSS mirrors
    SEC     = "sec"       # SEC EDGAR filings (Form 4, 8-K, 13F)
    WEBHOOK = "webhook"
    MANUAL  = "manual"


class Source(BaseModel):
    id:               str       = Field(default_factory=lambda: str(uuid.uuid4()))
    name:             str
    type:             SourceType
    url:              str       = ""   # feed URL or API base
    enabled:          bool      = True
    refresh_interval: int       = 300  # seconds between fetches
    config:           Dict[str, Any] = Field(default_factory=dict)

    last_fetched_at: Optional[datetime] = None
    last_error:      Optional[str]      = None
    error_count:     int                = 0
    total_fetched:   int                = 0

    class Config:
        use_enum_values = True
