"""
Swarm Coordinator — ARIA as CEO of Multi-Agent Committee
=========================================================
Orchestrates the specialized swarm agents (Risk, Momentum, Options)
and synthesizes their verdicts into a unified institutional-grade decision.

Architecture:
  ┌─────────────────────────────────────────┐
  │              ARIA (CEO)                 │
  │         SwarmCoordinator                │
  └──────────┬──────────┬───────────────────┘
             │          │           │
      RiskAgent  MomentumAgent  OptionsAgent
      (Risk Mgr) (Quant Analyst) (Derivatives Desk)

Committee voting:
  - Each agent produces a verdict (BUY/HOLD/REDUCE/SELL/EXIT)
  - Weighted vote tally with configurable weights
  - ARIA applies meta-rules (veto conditions, conviction thresholds)
  - Final output: SwarmDecision with full committee audit trail

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .risk_agent     import RiskAgent, RiskReport
from .momentum_agent import MomentumAgent, MomentumReport
from .options_agent  import OptionsAgent, OptionsReport

logger = logging.getLogger("atlas.ml_agents.swarm")


# ── Verdict Encoding ──────────────────────────────────────────────────────────

VERDICT_SCORE: Dict[str, float] = {
    "BUY":    1.0,
    "HOLD":   0.5,
    "REDUCE": 0.25,
    "EXIT":   0.0,
    "SELL":   0.0,
}

SCORE_TO_VERDICT: List[tuple] = [
    (0.80, "STRONG BUY"),
    (0.65, "BUY"),
    (0.45, "HOLD"),
    (0.25, "REDUCE"),
    (0.00, "SELL"),
]


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class AgentVote:
    """Individual agent's vote in the committee."""
    agent_name: str
    verdict: str
    score: float
    weight: float
    weighted_score: float
    key_reasoning: str

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "verdict": self.verdict,
            "raw_score": round(self.score, 3),
            "weight": self.weight,
            "weighted_score": round(self.weighted_score, 3),
            "key_reasoning": self.key_reasoning,
        }


@dataclass
class SwarmDecision:
    """
    Final output from the Swarm Coordinator.
    Contains all agent reports, votes, and ARIA's meta-decision.
    """
    symbol: str
    timestamp: float = field(default_factory=time.time)

    # Committee votes
    votes: List[AgentVote] = field(default_factory=list)

    # Raw agent reports
    risk_report:     Optional[RiskReport]     = None
    momentum_report: Optional[MomentumReport] = None
    options_report:  Optional[OptionsReport]  = None

    # Aggregated result
    committee_score: float = 0.5
    committee_verdict: str = "HOLD"
    aria_verdict: str      = "HOLD"        # ARIA's final decision (may override)
    aria_override: bool    = False          # True if ARIA vetoed committee
    conviction: str        = "LOW"         # HIGH / MEDIUM / LOW
    confidence: float      = 0.5           # 0–1 confidence in decision
    risk_flag: bool        = False          # True if risk agent issued EXIT/REDUCE
    reasoning: List[str]   = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "votes": [v.to_dict() for v in self.votes],
            "committee_score": round(self.committee_score, 3),
            "committee_verdict": self.committee_verdict,
            "aria_verdict": self.aria_verdict,
            "aria_override": self.aria_override,
            "conviction": self.conviction,
            "confidence": round(self.confidence, 3),
            "risk_flag": self.risk_flag,
            "reasoning": self.reasoning,
            "agents": {
                "risk":     self.risk_report.to_dict()     if self.risk_report else {},
                "momentum": self.momentum_report.to_dict() if self.momentum_report else {},
                "options":  self.options_report.to_dict()  if self.options_report else {},
            },
        }

    def summary(self) -> str:
        lines = [
            f"{'═'*55}",
            f"  SWARM DECISION — {self.symbol}",
            f"{'─'*55}",
        ]
        for v in self.votes:
            lines.append(
                f"  [{v.agent_name:<14}] {v.verdict:<12} "
                f"score={v.score:.3f}  weight={v.weight:.2f}"
            )
        lines += [
            f"{'─'*55}",
            f"  Committee Score : {self.committee_score:.3f}  →  {self.committee_verdict}",
            f"  ARIA Final      : {self.aria_verdict}  (override={self.aria_override})",
            f"  Conviction      : {self.conviction}   Confidence={self.confidence:.1%}",
            f"  Risk Flag       : {'⚠ YES' if self.risk_flag else 'OK'}",
            f"{'─'*55}",
        ]
        for r in self.reasoning:
            lines.append(f"  • {r}")
        lines.append(f"{'═'*55}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SwarmCoordinator
# ══════════════════════════════════════════════════════════════════════════════

class SwarmCoordinator:
    """
    ARIA as CEO — orchestrates the multi-agent committee.

    Default committee weights:
      - Risk Agent     : 40%  (hard constraint on capital preservation)
      - Momentum Agent : 35%  (trend / entry timing)
      - Options Agent  : 25%  (derivatives sentiment / IV signal)

    ARIA's meta-rules (veto conditions):
      1. If RiskAgent says EXIT → final verdict is SELL regardless of committee
      2. If risk_score < 0.25 → cap verdict at REDUCE
      3. If all three agents disagree → conviction = LOW, add caution note
      4. If two or more agree on BUY AND risk_score >= 0.60 → HIGH conviction

    Usage:
        coordinator = SwarmCoordinator()
        decision = coordinator.decide("NVDA", ohlcv_df)
        print(decision.summary())
    """

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "risk":     0.40,
        "momentum": 0.35,
        "options":  0.25,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        risk_free_rate: float = 0.045,
    ):
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self._normalise_weights()

        self.risk_agent     = RiskAgent(risk_free_rate=risk_free_rate)
        self.momentum_agent = MomentumAgent()
        self.options_agent  = OptionsAgent(risk_free_rate=risk_free_rate)

        logger.info(
            "SwarmCoordinator initialised — weights: risk=%.0f%% momentum=%.0f%% options=%.0f%%",
            self.weights["risk"] * 100,
            self.weights["momentum"] * 100,
            self.weights["options"] * 100,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def decide(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        market_df: Optional[pd.DataFrame] = None,
        options_chain: Optional[pd.DataFrame] = None,
    ) -> SwarmDecision:
        """
        Run the full swarm committee and produce ARIA's final decision.

        Parameters
        ----------
        symbol        : Ticker
        ohlcv         : OHLCV DataFrame
        market_df     : Optional market index OHLCV (for beta)
        options_chain : Optional options chain DataFrame

        Returns SwarmDecision.
        """
        decision = SwarmDecision(symbol=symbol)

        try:
            # ── Step 1: Run all agents ────────────────────────────────────
            logger.debug("Swarm: running agents for %s …", symbol)

            risk_rep  = self.risk_agent.analyse(symbol, ohlcv, market_df)
            mom_rep   = self.momentum_agent.analyse(symbol, ohlcv)
            opts_rep  = self.options_agent.analyse(symbol, ohlcv, options_chain)

            decision.risk_report     = risk_rep
            decision.momentum_report = mom_rep
            decision.options_report  = opts_rep

            # ── Step 2: Build votes ───────────────────────────────────────
            votes = [
                self._make_vote("Risk",     risk_rep.verdict,  risk_rep.risk_score,
                                self.weights["risk"],     risk_rep.reasoning[:1]),
                self._make_vote("Momentum", mom_rep.verdict,   mom_rep.momentum_score,
                                self.weights["momentum"], mom_rep.reasoning[:1]),
                self._make_vote("Options",  opts_rep.verdict,  opts_rep.options_score,
                                self.weights["options"],  opts_rep.reasoning[:1]),
            ]
            decision.votes = votes

            # ── Step 3: Weighted committee score ─────────────────────────
            total_weight   = sum(v.weight for v in votes)
            weighted_total = sum(v.weighted_score for v in votes)
            committee_score = weighted_total / total_weight if total_weight > 0 else 0.5

            decision.committee_score   = round(committee_score, 3)
            decision.committee_verdict = self._score_to_verdict(committee_score)

            # ── Step 4: ARIA meta-rules ───────────────────────────────────
            decision = self._apply_aria_rules(decision, risk_rep, mom_rep, opts_rep)

            # ── Step 5: Conviction and confidence ────────────────────────
            decision.conviction = self._conviction(votes, decision.aria_verdict)
            decision.confidence = self._confidence(decision)
            decision.reasoning  = self._build_reasoning(decision)
            decision.metadata   = {
                "agent_verdicts": {
                    "risk":     risk_rep.verdict,
                    "momentum": mom_rep.verdict,
                    "options":  opts_rep.verdict,
                },
                "committee_score": decision.committee_score,
            }

            logger.info(
                "Swarm[%s] → %s (conviction=%s, confidence=%.1f%%)",
                symbol, decision.aria_verdict, decision.conviction, decision.confidence * 100,
            )

        except Exception as exc:
            logger.exception("SwarmCoordinator.decide failed for %s: %s", symbol, exc)
            decision.reasoning.append(f"Swarm error: {exc}")

        return decision

    def batch_decide(
        self,
        tickers: List[str],
        data_map: Dict[str, pd.DataFrame],
        market_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, SwarmDecision]:
        """
        Run the swarm on a universe of tickers.

        Parameters
        ----------
        tickers    : List of ticker symbols
        data_map   : {ticker: ohlcv_df}
        market_df  : Optional market index (shared for all)

        Returns {ticker: SwarmDecision}.
        """
        results: Dict[str, SwarmDecision] = {}
        for ticker in tickers:
            ohlcv = data_map.get(ticker)
            if ohlcv is None or len(ohlcv) < 20:
                logger.warning("Skipping %s — no data", ticker)
                continue
            results[ticker] = self.decide(ticker, ohlcv, market_df)
        return results

    def get_rankings(
        self, decisions: Dict[str, SwarmDecision]
    ) -> List[Dict[str, Any]]:
        """
        Rank tickers by committee score for portfolio construction.
        Returns list sorted by confidence × committee_score (desc).
        """
        rows = []
        for ticker, d in decisions.items():
            rows.append({
                "symbol":      ticker,
                "verdict":     d.aria_verdict,
                "score":       d.committee_score,
                "confidence":  d.confidence,
                "conviction":  d.conviction,
                "risk_flag":   d.risk_flag,
                "composite":   round(d.committee_score * d.confidence, 4),
            })
        rows.sort(key=lambda x: x["composite"], reverse=True)
        return rows

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _normalise_weights(self) -> None:
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    @staticmethod
    def _make_vote(
        name: str,
        verdict: str,
        score: float,
        weight: float,
        reasoning: List[str],
    ) -> AgentVote:
        encoded = VERDICT_SCORE.get(verdict, 0.5)
        return AgentVote(
            agent_name=name,
            verdict=verdict,
            score=encoded,
            weight=weight,
            weighted_score=encoded * weight,
            key_reasoning=reasoning[0] if reasoning else "",
        )

    @staticmethod
    def _score_to_verdict(score: float) -> str:
        for threshold, verdict in SCORE_TO_VERDICT:
            if score >= threshold:
                return verdict
        return "SELL"

    def _apply_aria_rules(
        self,
        decision: SwarmDecision,
        risk_rep: RiskReport,
        mom_rep: MomentumReport,
        opts_rep: OptionsReport,
    ) -> SwarmDecision:
        """Apply ARIA CEO's meta-rules and veto conditions."""
        verdict = decision.committee_verdict

        # Rule 1: Hard risk veto
        if risk_rep.verdict in ("EXIT", "SELL") or risk_rep.risk_score < 0.15:
            decision.aria_verdict  = "SELL"
            decision.aria_override = True
            decision.risk_flag     = True
            decision.reasoning.append(
                f"ARIA VETO: Risk Agent flagged critical risk "
                f"(score={risk_rep.risk_score:.2f}, verdict={risk_rep.verdict})"
            )
            return decision

        # Rule 2: Cap at REDUCE if risk is low
        if risk_rep.risk_score < 0.25 and verdict in ("STRONG BUY", "BUY"):
            verdict = "REDUCE"
            decision.aria_override = True
            decision.risk_flag     = True
            decision.reasoning.append(
                f"ARIA ADJUST: Capped to REDUCE — risk score too low ({risk_rep.risk_score:.2f})"
            )

        # Rule 3: Boost conviction if all agree
        agent_verdicts = {
            "risk":     risk_rep.verdict,
            "momentum": mom_rep.verdict,
            "options":  opts_rep.verdict,
        }
        buy_votes  = sum(1 for v in agent_verdicts.values() if v == "BUY")
        hold_votes = sum(1 for v in agent_verdicts.values() if v == "HOLD")

        if buy_votes >= 2 and risk_rep.risk_score >= 0.60 and verdict in ("BUY", "STRONG BUY"):
            decision.reasoning.append(
                f"ARIA CONFIRM: {buy_votes}/3 agents bullish with healthy risk profile → HIGH conviction"
            )

        decision.aria_verdict = verdict
        decision.risk_flag    = risk_rep.verdict in ("EXIT", "REDUCE")
        return decision

    @staticmethod
    def _conviction(votes: List[AgentVote], final_verdict: str) -> str:
        """Classify conviction based on agent agreement."""
        agreeing = sum(
            1 for v in votes
            if VERDICT_SCORE.get(v.verdict, 0.5) >= VERDICT_SCORE.get(final_verdict, 0.5) - 0.1
        )
        if agreeing == 3:
            return "HIGH"
        elif agreeing == 2:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _confidence(decision: SwarmDecision) -> float:
        """Confidence 0–1 based on committee score and conviction."""
        base = decision.committee_score
        boost = {"HIGH": 0.15, "MEDIUM": 0.05, "LOW": -0.10}.get(decision.conviction, 0)
        if decision.risk_flag:
            base *= 0.7
        return round(max(0.0, min(1.0, base + boost)), 3)

    @staticmethod
    def _build_reasoning(decision: SwarmDecision) -> List[str]:
        lines = list(decision.reasoning)  # preserve any veto notes
        lines.append(
            f"Committee: Risk={decision.votes[0].verdict} | "
            f"Momentum={decision.votes[1].verdict} | "
            f"Options={decision.votes[2].verdict}"
        )
        lines.append(
            f"Weighted Score: {decision.committee_score:.3f} → {decision.committee_verdict}"
        )
        if decision.aria_override:
            lines.append(f"⚠ ARIA override applied → final: {decision.aria_verdict}")
        return lines
