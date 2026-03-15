"""
SignalService — orchestrates the full ingestion pipeline for a batch of RawItems.

Flow:
  RawItem[]  →  Normalizer  →  Deduper  →  Classifier  →  Matcher  →  Scorer
  → storage.insert_signal + insert_match  → AlertService  → WhaleService
"""
from __future__ import annotations
import logging
from typing import List, Tuple

from ..collectors.base import RawItem
from ..models import Match, Signal
from ..pipeline import Classifier, Deduper, Matcher, Normalizer, Scorer
from ..storage import SignalRepository
from .alert_service import AlertService
from .whale_service import WhaleService

logger = logging.getLogger(__name__)


class SignalService:
    def __init__(
        self,
        repo: SignalRepository,
        alert_service: AlertService,
        whale_service: WhaleService,
    ):
        self._repo           = repo
        self._alert_service  = alert_service
        self._whale_service  = whale_service
        self._normalizer     = Normalizer()
        self._deduper        = Deduper(repo)
        self._classifier     = Classifier()
        self._scorer         = Scorer()

    def ingest(self, raw_items: List[RawItem]) -> Tuple[int, int]:
        """
        Process a batch of raw items.
        Returns (inserted_count, duplicate_count).
        """
        if not raw_items:
            return 0, 0

        # 1. Normalize
        signals: List[Signal] = [self._normalizer.normalize(r) for r in raw_items]

        # 2. Dedup
        before = len(signals)
        signals = self._deduper.filter(signals)
        dupes   = before - len(signals)

        if not signals:
            return 0, dupes

        # 3. Classify
        for sig in signals:
            self._classifier.classify(sig)

        # 4. Match against watchlist
        watchlist = self._repo.get_watchlist()
        matcher   = Matcher(watchlist)
        all_matches: List[Match] = []
        signal_matches: dict[str, List[Match]] = {}
        for sig in signals:
            matches = matcher.match(sig)
            signal_matches[sig.id] = matches
            all_matches.extend(matches)

        # 5. Score
        for sig in signals:
            self._scorer.score(sig, signal_matches.get(sig.id, []))

        # 6. Persist
        inserted = 0
        for sig in signals:
            try:
                self._repo.insert_signal(sig)
                for m in signal_matches.get(sig.id, []):
                    self._repo.insert_match(m)
                inserted += 1
            except Exception as exc:
                logger.error("[SignalService] persist error for %s: %s", sig.id, exc)

        # 7. Fire alerts
        for sig in signals:
            try:
                self._alert_service.evaluate(sig, signal_matches.get(sig.id, []))
            except Exception as exc:
                logger.warning("[SignalService] alert error: %s", exc)

        # 8. Extract whale events
        for sig in signals:
            try:
                self._whale_service.detect(sig)
            except Exception as exc:
                logger.warning("[SignalService] whale detect error: %s", exc)

        logger.info("[SignalService] ingested %d / dupes %d from batch of %d", inserted, dupes, before)
        return inserted, dupes

    def query(self, **kwargs) -> List[Signal]:
        return self._repo.get_signals(**kwargs)

    def get_signal(self, signal_id: str):
        return self._repo.get_signal(signal_id)

    def get_stats(self):
        return self._repo.get_stats()
