"""
Match — a signal linked to a watchlist item.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MatchType(str, Enum):
    EXACT   = "exact"    # ticker symbol found verbatim in title/body
    FUZZY   = "fuzzy"    # company name / alias matched
    KEYWORD = "keyword"  # sector/theme keyword matched


class Match(BaseModel):
    id:                str       = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id:         str
    watchlist_item_id: str
    ticker:            str
    match_type:        MatchType = MatchType.EXACT
    match_score:       float     = 1.0   # 0.0 … 1.0
    created_at:        datetime  = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
