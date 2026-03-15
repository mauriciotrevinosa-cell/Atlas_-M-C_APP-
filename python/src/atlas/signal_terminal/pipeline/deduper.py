"""
Deduper — filters out signals already seen in the database.
Uses content_hash for exact-match deduplication.
"""
from __future__ import annotations
import logging
from typing import List

from ..models import Signal
from ..storage import SignalRepository

logger = logging.getLogger(__name__)


class Deduper:
    def __init__(self, repo: SignalRepository):
        self._repo = repo

    def filter(self, signals: List[Signal]) -> List[Signal]:
        """Return only signals whose content_hash has not been stored before."""
        unique: List[Signal] = []
        for sig in signals:
            if not sig.content_hash:
                unique.append(sig)
                continue
            if self._repo.hash_exists(sig.content_hash):
                logger.debug("[Dedup] skip duplicate hash=%s title=%r", sig.content_hash[:8], sig.title[:60])
            else:
                unique.append(sig)
        return unique
