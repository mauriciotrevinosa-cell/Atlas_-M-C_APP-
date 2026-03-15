"""
WhaleEvent — large transaction or unusual market activity.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class WhaleEventType(str, Enum):
    LARGE_BUY        = "large_buy"
    LARGE_SELL       = "large_sell"
    UNUSUAL_OPTIONS  = "unusual_options"   # high OI or volume vs open interest
    DARK_POOL        = "dark_pool"         # off-exchange block trade
    INSIDER          = "insider"           # SEC Form 4 / insider transaction
    SHORT_SQUEEZE    = "short_squeeze"     # short interest spike
    BLOCK_TRADE      = "block_trade"       # >$1M single trade
    UNKNOWN          = "unknown"


_SIZE_LABELS = [
    (1_000_000_000, "$1B+"),
    (500_000_000,   "$500M+"),
    (100_000_000,   "$100M+"),
    (50_000_000,    "$50M+"),
    (10_000_000,    "$10M+"),
    (1_000_000,     "$1M+"),
]


def _size_label(dollars: Optional[float]) -> str:
    if dollars is None:
        return "unknown"
    for threshold, label in _SIZE_LABELS:
        if dollars >= threshold:
            return label
    return f"${dollars:,.0f}"


class WhaleEvent(BaseModel):
    id:          str  = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id:   Optional[str] = None   # FK to Signal if derived from one
    ticker:      str
    event_type:  WhaleEventType = WhaleEventType.UNKNOWN
    size:        Optional[float] = None   # USD value
    size_label:  str              = ""    # computed on validation
    description: str              = ""
    source:      str              = ""    # where it was detected
    confidence:  float            = 0.5   # 0.0 … 1.0
    detected_at: datetime         = Field(default_factory=datetime.utcnow)

    def model_post_init(self, __context):
        if not self.size_label:
            object.__setattr__(self, "size_label", _size_label(self.size))

    class Config:
        use_enum_values = True
