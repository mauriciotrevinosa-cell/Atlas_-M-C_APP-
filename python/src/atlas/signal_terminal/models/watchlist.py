"""
WatchlistItem — a ticker/asset to monitor.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class AssetType(str, Enum):
    STOCK  = "stock"
    CRYPTO = "crypto"
    ETF    = "etf"
    OPTION = "option"
    FUTURE = "future"
    OTHER  = "other"


class WatchPriority(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class WatchlistItem(BaseModel):
    id:            str           = Field(default_factory=lambda: str(uuid.uuid4()))
    ticker:        str
    name:          Optional[str] = None
    asset_type:    AssetType     = AssetType.STOCK
    priority:      WatchPriority = WatchPriority.MEDIUM
    tags:          List[str]     = Field(default_factory=list)
    notes:         Optional[str] = None
    alert_enabled: bool          = True
    added_at:      datetime      = Field(default_factory=datetime.utcnow)

    # Aliases used for fuzzy matching (e.g. "Apple", "AAPL", "Apple Inc")
    aliases: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
