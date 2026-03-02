"""
Signal Compositor — Fase 5
===========================
Combines signals from ALL Atlas engines (rule-based, ML, RL) into a
single final OrderProposal with risk-aware position sizing.

Sizing methods
--------------
• Kelly Criterion (fractional)  — f* = (p(b+1)−1) / b, capped at max_kelly
• Volatility Scaling            — size ∝ target_vol / realized_vol
• Confidence Weighting          — linear scale from 0..1 confidence
• Hard guardrails               — max per-trade %, max daily loss, min confidence

Output
------
OrderProposal   — action, size_pct, dollar_amount, confidence, reasoning

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.signal_composition")

# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class Signal:
    """Normalised signal from any engine."""
    engine_id:  str
    action:     str          # 'LONG' | 'SHORT' | 'HOLD'
    confidence: float        # 0.0 – 1.0
    weight:     float = 1.0  # engine weight in the compositor
    metadata:   Dict  = field(default_factory=dict)


@dataclass
class OrderProposal:
    """Final composed order proposal sent to the execution layer."""
    action:         str          # 'BUY' | 'SELL' | 'HOLD'
    size_pct:       float        # % of capital to deploy (0–max_position)
    dollar_amount:  float        # size_pct × capital
    confidence:     float        # composite confidence 0–1
    kelly_fraction: float        # raw Kelly fraction before clipping
    vol_scalar:     float        # volatility scaling factor applied
    engine_votes:   Dict[str, str] = field(default_factory=dict)
    reasoning:      str = ""
    blocked:        bool = False
    block_reason:   str = ""

    def to_dict(self) -> Dict:
        return {
            "action":         self.action,
            "size_pct":       round(self.size_pct * 100, 2),
            "dollar_amount":  round(self.dollar_amount, 2),
            "confidence":     round(self.confidence, 4),
            "kelly_fraction": round(self.kelly_fraction, 4),
            "vol_scalar":     round(self.vol_scalar, 4),
            "engine_votes":   self.engine_votes,
            "reasoning":      self.reasoning,
            "blocked":        self.blocked,
            "block_reason":   self.block_reason,
        }


# ── Position sizing helpers ────────────────────────────────────────────────────

def kelly_fraction(
    win_rate: float,
    avg_win:  float,
    avg_loss: float,
    max_fraction: float = 0.25,
) -> float:
    """
    Fractional Kelly criterion.

    f* = (p × b − q) / b   where b = avg_win/avg_loss, p = win_rate, q = 1−p.

    Clipped to [0, max_fraction] and halved (half-Kelly) for robustness.
    """
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    b = avg_win / (avg_loss + 1e-9)
    q = 1.0 - win_rate
    f = (win_rate * b - q) / (b + 1e-9)
    # Half-Kelly for robustness
    f = f * 0.5
    return float(np.clip(f, 0.0, max_fraction))


def volatility_scalar(
    ohlcv: pd.DataFrame,
    target_vol: float = 0.15,
    lookback:   int   = 20,
) -> float:
    """
    Vol-targeting scalar: returns target_vol / realized_vol.

    Clipped to [0.25, 4.0] to prevent extreme leverage or near-zero sizing.
    """
    if ohlcv is None or len(ohlcv) < lookback + 1:
        return 1.0
    rets = ohlcv["Close"].pct_change().dropna()
    realized = float(rets.tail(lookback).std() * np.sqrt(252))
    if realized < 1e-6:
        return 1.0
    scalar = target_vol / realized
    return float(np.clip(scalar, 0.25, 4.0))


def consensus_action(signals: List[Signal]) -> tuple[str, float]:
    """
    Weighted majority vote over signal list.

    Returns (action, composite_confidence).
    """
    if not signals:
        return "HOLD", 0.0

    vote_map = {"LONG": 1.0, "HOLD": 0.0, "SHORT": -1.0}
    total_w, weighted_sum = 0.0, 0.0

    for sig in signals:
        v = vote_map.get(sig.action.upper(), 0.0)
        total_w       += sig.weight
        weighted_sum  += v * sig.confidence * sig.weight

    if total_w < 1e-9:
        return "HOLD", 0.0

    score = weighted_sum / total_w   # −1 .. +1
    conf  = min(1.0, abs(score))

    if score > 0.15:
        action = "LONG"
    elif score < -0.15:
        action = "SHORT"
    else:
        action = "HOLD"

    return action, round(conf, 4)


# ── Main compositor ────────────────────────────────────────────────────────────

class SignalCompositor:
    """
    Combines engine signals → single OrderProposal with risk-aware sizing.

    Parameters
    ----------
    capital        : total portfolio capital in $
    target_vol     : annualised volatility target (default 15%)
    max_position   : hard cap on position size as fraction of capital (default 10%)
    min_confidence : minimum composite confidence to generate a non-HOLD order
    max_kelly      : maximum Kelly fraction before vol-scaling (default 25%)
    guardrails     : dict of runtime limits (daily_loss_pct, max_drawdown_pct)
    """

    def __init__(
        self,
        capital:        float = 100_000.0,
        target_vol:     float = 0.15,
        max_position:   float = 0.10,
        min_confidence: float = 0.40,
        max_kelly:      float = 0.25,
        guardrails:     Optional[Dict] = None,
    ):
        self.capital        = capital
        self.target_vol     = target_vol
        self.max_position   = max_position
        self.min_confidence = min_confidence
        self.max_kelly      = max_kelly
        self.guardrails     = guardrails or {
            "daily_loss_pct":  0.02,   # 2% daily loss limit
            "max_drawdown_pct": 0.10,  # 10% max drawdown
        }

        # Runtime state (updated by caller)
        self._daily_pnl_pct:  float = 0.0
        self._current_dd_pct: float = 0.0

        # Historical accuracy per engine (updated by CalibrationEngine)
        self._engine_stats: Dict[str, Dict] = {}

    # ── Calibration hooks ──────────────────────────────────────────────────────

    def set_engine_stats(self, engine_id: str, win_rate: float,
                         avg_win: float, avg_loss: float):
        """Set historical accuracy stats for Kelly calculation."""
        self._engine_stats[engine_id] = {
            "win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss,
        }

    def update_runtime_state(self, daily_pnl_pct: float, drawdown_pct: float):
        """Called by AutoTrader after each bar to enforce guardrails."""
        self._daily_pnl_pct   = daily_pnl_pct
        self._current_dd_pct  = drawdown_pct

    # ── Core compose ──────────────────────────────────────────────────────────

    def compose(
        self,
        signals:    List[Signal],
        ohlcv:      Optional[pd.DataFrame] = None,
        context:    Optional[Dict]          = None,
    ) -> OrderProposal:
        """
        Main entry point.

        Parameters
        ----------
        signals : list of Signal objects from all engines
        ohlcv   : OHLCV DataFrame for volatility scaling
        context : optional dict with ticker, capital override, etc.

        Returns
        -------
        OrderProposal with full sizing, confidence, and reasoning
        """
        if context and "capital" in context:
            capital = float(context["capital"])
        else:
            capital = self.capital

        engine_votes = {s.engine_id: s.action for s in signals}

        # ── Guardrail checks ──────────────────────────────────────────────────
        block, reason = self._check_guardrails()
        if block:
            return OrderProposal(
                action="HOLD", size_pct=0.0, dollar_amount=0.0,
                confidence=0.0, kelly_fraction=0.0, vol_scalar=1.0,
                engine_votes=engine_votes, blocked=True, block_reason=reason,
                reasoning=f"BLOCKED: {reason}",
            )

        # ── Consensus action + composite confidence ───────────────────────────
        action, conf = consensus_action(signals)

        if conf < self.min_confidence or action == "HOLD":
            return OrderProposal(
                action="HOLD", size_pct=0.0, dollar_amount=0.0,
                confidence=conf, kelly_fraction=0.0, vol_scalar=1.0,
                engine_votes=engine_votes,
                reasoning=f"Composite confidence {conf:.1%} below threshold "
                          f"{self.min_confidence:.1%} or HOLD consensus.",
            )

        # ── Kelly fraction ────────────────────────────────────────────────────
        # Aggregate stats across engines, weighted by signal confidence
        total_w, wr_sum, win_sum, loss_sum = 0.0, 0.0, 0.0, 0.0
        for sig in signals:
            stats = self._engine_stats.get(sig.engine_id)
            if stats:
                w = sig.confidence * sig.weight
                wr_sum   += stats["win_rate"] * w
                win_sum  += stats["avg_win"]  * w
                loss_sum += stats["avg_loss"] * w
                total_w  += w

        if total_w > 0:
            agg_wr  = wr_sum  / total_w
            agg_win = win_sum / total_w
            agg_los = loss_sum / total_w
            k_frac  = kelly_fraction(agg_wr, agg_win, agg_los, self.max_kelly)
        else:
            # No stats available → use confidence-proportional sizing
            k_frac = conf * self.max_kelly * 0.5

        # ── Volatility scaling ────────────────────────────────────────────────
        vol_sc = volatility_scalar(ohlcv, self.target_vol) if ohlcv is not None else 1.0

        # ── Final size ────────────────────────────────────────────────────────
        raw_size  = k_frac * vol_sc * conf
        size_pct  = min(raw_size, self.max_position)
        dollar_amt = size_pct * capital

        # Map LONG/SHORT to BUY/SELL
        final_action = "BUY" if action == "LONG" else "SELL"

        reasoning = (
            f"Consensus: {action} | Conf: {conf:.1%} | "
            f"Kelly: {k_frac:.3f} | Vol scalar: {vol_sc:.2f} | "
            f"Size: {size_pct:.1%} of capital (${dollar_amt:,.0f})"
        )

        return OrderProposal(
            action=final_action,
            size_pct=size_pct,
            dollar_amount=dollar_amt,
            confidence=conf,
            kelly_fraction=k_frac,
            vol_scalar=vol_sc,
            engine_votes=engine_votes,
            reasoning=reasoning,
        )

    # ── Guardrail checks ──────────────────────────────────────────────────────

    def _check_guardrails(self) -> tuple[bool, str]:
        g = self.guardrails
        if self._daily_pnl_pct < -g.get("daily_loss_pct", 0.02):
            return True, f"Daily loss limit hit ({self._daily_pnl_pct:.1%})"
        if self._current_dd_pct > g.get("max_drawdown_pct", 0.10):
            return True, f"Max drawdown exceeded ({self._current_dd_pct:.1%})"
        return False, ""

    # ── Scenario analysis ────────────────────────────────────────────────────

    def size_scenarios(
        self,
        base_confidence: float = 0.6,
        ohlcv: Optional[pd.DataFrame] = None,
    ) -> List[Dict]:
        """
        Returns sizing across confidence levels for UI display.
        Useful for position sizing calculator panel.
        """
        vol_sc = volatility_scalar(ohlcv, self.target_vol) if ohlcv is not None else 1.0
        rows = []
        for conf in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            k = conf * self.max_kelly * 0.5
            sz = min(k * vol_sc * conf, self.max_position)
            rows.append({
                "confidence": round(conf, 2),
                "kelly":      round(k, 4),
                "size_pct":   round(sz * 100, 2),
                "dollar":     round(sz * self.capital, 0),
                "vol_scalar": round(vol_sc, 3),
            })
        return rows
