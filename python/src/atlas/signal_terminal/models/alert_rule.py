"""
AlertRule — when-to-fire and what-to-do configuration.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class AlertAction(str, Enum):
    LOG      = "log"       # write to alert log only
    TELEGRAM = "telegram"  # Telegram bot message (requires TELEGRAM_BOT_TOKEN env)
    DISCORD  = "discord"   # Discord webhook POST
    WEBHOOK  = "webhook"   # POST to arbitrary URL


class AlertRule(BaseModel):
    id:      str  = Field(default_factory=lambda: str(uuid.uuid4()))
    name:    str
    enabled: bool = True

    # Conditions (all must match — AND logic)
    # Supported keys:
    #   ticker          : str | list[str]
    #   category        : str | list[str]
    #   sentiment       : "bullish" | "bearish" | "neutral"
    #   urgency         : "low" | "medium" | "high" | "critical"
    #   relevance_min   : float  (0.0–1.0)
    #   source_id       : str | list[str]
    #   keywords_any    : list[str]   (any keyword must be present)
    conditions: Dict[str, Any] = Field(default_factory=dict)

    action:        AlertAction        = AlertAction.LOG
    action_config: Dict[str, Any]     = Field(default_factory=dict)

    created_at:        datetime           = Field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    trigger_count:     int                = 0

    class Config:
        use_enum_values = True
