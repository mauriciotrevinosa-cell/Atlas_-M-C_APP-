"""
Pattern Memory — Fase 10
=========================
Vectorised similarity search over historical market states.
Finds past regimes that closely resemble the current state.

Components
----------
MarketSnapshot     — feature vector of current market state
PatternMemory      — stores snapshots, similarity search (cosine/euclidean)
RegimeMemory       — tracks which regime labels occurred in which contexts
MemoryStore (enhanced) — persistence layer with pattern + regime memory

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("atlas.memory")


# ── Market Snapshot ───────────────────────────────────────────────────────────

@dataclass
class MarketSnapshot:
    """
    Compact vector representation of a market state.

    Features (all normalised to ≈[−1, 1] or [0, 1])
    ---------
    trend_score      : SMA-cross trend strength  −1..+1
    vol_percentile   : realised-vol percentile vs 1y  0..1
    rsi              : RSI / 100  0..1
    momentum_5d      : 5d return  (clipped ±0.2)
    momentum_20d     : 20d return (clipped ±0.4)
    regime_code      : encoded regime  {trending:1, ranging:0, volatile:-1}
    confidence       : signal composite confidence  0..1
    """
    timestamp:     str
    ticker:        str
    trend_score:   float = 0.0
    vol_percentile:float = 0.5
    rsi:           float = 0.5
    momentum_5d:   float = 0.0
    momentum_20d:  float = 0.0
    regime_code:   float = 0.0
    confidence:    float = 0.0
    label:         str   = ""   # e.g. outcome label set post-hoc
    metadata:      Dict  = field(default_factory=dict)

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.trend_score,
            self.vol_percentile,
            self.rsi,
            np.clip(self.momentum_5d,  -0.2, 0.2) / 0.2,
            np.clip(self.momentum_20d, -0.4, 0.4) / 0.4,
            self.regime_code,
            self.confidence,
        ], dtype=float)

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d


# ── Similarity Search ─────────────────────────────────────────────────────────

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)


def _euclidean_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Convert L2 distance to similarity score in [0, 1]."""
    dist = np.linalg.norm(a - b)
    return float(1.0 / (1.0 + dist))


# ── Pattern Memory ────────────────────────────────────────────────────────────

class PatternMemory:
    """
    Stores a rolling buffer of MarketSnapshots.
    On query, returns the k most similar past states.

    Parameters
    ----------
    max_size   : max snapshots to keep (FIFO eviction)
    metric     : 'cosine' | 'euclidean'
    """

    def __init__(self, max_size: int = 2000, metric: str = "cosine"):
        self.max_size  = max_size
        self.metric    = metric
        self._snaps:   List[MarketSnapshot] = []
        self._vectors: Optional[np.ndarray] = None  # (N, D) cache

    def add(self, snap: MarketSnapshot):
        """Add a snapshot, evict oldest if over max_size."""
        self._snaps.append(snap)
        if len(self._snaps) > self.max_size:
            self._snaps.pop(0)
        self._vectors = None  # invalidate cache

    def _build_matrix(self) -> np.ndarray:
        if self._vectors is None:
            if not self._snaps:
                self._vectors = np.empty((0, 7))
            else:
                self._vectors = np.vstack([s.to_vector() for s in self._snaps])
        return self._vectors

    def query(
        self,
        snap: MarketSnapshot,
        k: int = 5,
        min_similarity: float = 0.5,
        exclude_same_ticker: bool = False,
    ) -> List[Tuple[MarketSnapshot, float]]:
        """
        Find k most similar past snapshots.

        Returns
        -------
        List of (snapshot, similarity_score) sorted descending.
        """
        mat = self._build_matrix()
        if mat.shape[0] == 0:
            return []

        q = snap.to_vector()

        if self.metric == "cosine":
            scores = np.array([_cosine_sim(q, mat[i]) for i in range(len(mat))])
        else:
            scores = np.array([_euclidean_sim(q, mat[i]) for i in range(len(mat))])

        # Filter
        candidates = []
        for i, sc in enumerate(scores):
            s = self._snaps[i]
            if exclude_same_ticker and s.ticker == snap.ticker:
                continue
            if sc >= min_similarity:
                candidates.append((s, float(sc)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:k]

    def outcome_statistics(
        self,
        snap: MarketSnapshot,
        k: int = 10,
    ) -> Dict:
        """
        Query similar states and compute outcome statistics
        (requires 'label' field to be set on historical snapshots).

        Returns
        -------
        {
          "n_similar":    int,
          "label_counts": {label: count},
          "dominant":     str (most common label),
          "avg_sim":      float,
        }
        """
        results = self.query(snap, k=k)
        if not results:
            return {"n_similar": 0, "label_counts": {}, "dominant": "UNKNOWN", "avg_sim": 0.0}

        label_counts: Dict[str, int] = {}
        sims = []
        for s, sc in results:
            lb = s.label or "UNLABELED"
            label_counts[lb] = label_counts.get(lb, 0) + 1
            sims.append(sc)

        dominant = max(label_counts, key=label_counts.get)
        return {
            "n_similar":    len(results),
            "label_counts": label_counts,
            "dominant":     dominant,
            "avg_sim":      round(float(np.mean(sims)), 4),
        }

    def to_list(self) -> List[Dict]:
        return [s.to_dict() for s in self._snaps]

    def from_list(self, records: List[Dict]):
        self._snaps = [MarketSnapshot(**r) for r in records]
        self._vectors = None

    def __len__(self):
        return len(self._snaps)


# ── Regime Memory ─────────────────────────────────────────────────────────────

class RegimeMemory:
    """
    Tracks regime transitions and associated performance.

    Usage
    -----
    rm = RegimeMemory()
    rm.record_transition("trending", "volatile", pnl=-0.02)
    rm.transition_stats("trending")   # → likely next regimes + avg P&L
    """

    def __init__(self):
        self._transitions: List[Dict] = []   # {from, to, pnl, timestamp}
        self._regime_pnl: Dict[str, List[float]] = {}

    def record_transition(
        self,
        from_regime: str,
        to_regime:   str,
        pnl:         float = 0.0,
    ):
        self._transitions.append({
            "from": from_regime,
            "to":   to_regime,
            "pnl":  pnl,
            "ts":   datetime.now().isoformat(),
        })
        self._regime_pnl.setdefault(from_regime, []).append(pnl)

    def transition_stats(self, from_regime: str) -> Dict:
        """
        What regimes tend to follow `from_regime`, and what P&L was typical?
        """
        relevant = [t for t in self._transitions if t["from"] == from_regime]
        if not relevant:
            return {"n": 0, "next_regimes": {}, "avg_pnl": 0.0}

        next_counts: Dict[str, int] = {}
        pnls = []
        for t in relevant:
            next_counts[t["to"]] = next_counts.get(t["to"], 0) + 1
            pnls.append(t["pnl"])

        total = len(relevant)
        next_probs = {k: round(v / total, 3) for k, v in next_counts.items()}

        return {
            "n":             total,
            "next_regimes":  next_probs,
            "avg_pnl":       round(float(np.mean(pnls)), 4),
            "pnl_std":       round(float(np.std(pnls)), 4),
        }

    def regime_performance(self) -> Dict[str, Dict]:
        """Summarise average P&L per regime."""
        out = {}
        for regime, pnls in self._regime_pnl.items():
            arr = np.array(pnls)
            out[regime] = {
                "avg_pnl":   round(float(arr.mean()), 4),
                "std_pnl":   round(float(arr.std()), 4),
                "win_rate":  round(float((arr > 0).mean()), 4),
                "n_trades":  len(pnls),
            }
        return out

    def to_list(self) -> List[Dict]:
        return list(self._transitions)

    def from_list(self, records: List[Dict]):
        self._transitions = records
        self._regime_pnl = {}
        for t in records:
            self._regime_pnl.setdefault(t["from"], []).append(t.get("pnl", 0.0))


# ── Enhanced Memory Store ─────────────────────────────────────────────────────

class EnhancedMemoryStore:
    """
    Persistence layer combining MemoryStore + PatternMemory + RegimeMemory.

    Persists to a single JSON file.
    """

    def __init__(
        self,
        path: str = "data/memory_enhanced.json",
        max_patterns: int = 2000,
        metric: str = "cosine",
    ):
        self.path            = Path(path)
        self.pattern_memory  = PatternMemory(max_size=max_patterns, metric=metric)
        self.regime_memory   = RegimeMemory()
        self._runs: List[Dict] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                self._runs = data.get("runs", [])
                self.pattern_memory.from_list(data.get("patterns", []))
                self.regime_memory.from_list(data.get("transitions", []))
                logger.info(
                    "Memory loaded: %d runs, %d patterns, %d transitions",
                    len(self._runs),
                    len(self.pattern_memory),
                    len(self.regime_memory.to_list()),
                )
            except Exception as e:
                logger.warning("Memory load error: %s", e)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "runs":        self._runs,
            "patterns":    self.pattern_memory.to_list(),
            "transitions": self.regime_memory.to_list(),
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def save_run(self, run_data: Dict):
        """Save a backtest or live run result."""
        self._runs.append({
            "timestamp": datetime.now().isoformat(),
            "data":      run_data,
        })
        self.save()

    def add_snapshot(self, snap: MarketSnapshot, auto_save: bool = False):
        """Add a market state snapshot to pattern memory."""
        self.pattern_memory.add(snap)
        if auto_save:
            self.save()

    def find_similar(
        self, snap: MarketSnapshot, k: int = 5
    ) -> List[Tuple[MarketSnapshot, float]]:
        """Find k most similar historical states."""
        return self.pattern_memory.query(snap, k=k)

    def record_regime_transition(
        self, from_regime: str, to_regime: str, pnl: float = 0.0
    ):
        self.regime_memory.record_transition(from_regime, to_regime, pnl)

    def memory_summary(self) -> Dict:
        return {
            "n_runs":        len(self._runs),
            "n_patterns":    len(self.pattern_memory),
            "n_transitions": len(self.regime_memory.to_list()),
            "regime_perf":   self.regime_memory.regime_performance(),
        }
