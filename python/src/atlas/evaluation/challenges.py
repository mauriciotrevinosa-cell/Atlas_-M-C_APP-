"""
Atlas challenge evaluation.

Small, deterministic scoring layer for comparing strategy, agent, or research
runs. Inspired by challenge/leaderboard ideas from intake repos, rebuilt as
Atlas-owned code that consumes existing metrics instead of creating a new app.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


@dataclass(slots=True)
class ChallengeSpec:
    name: str = "Atlas Research Challenge"
    initial_capital: float = 100_000.0
    max_drawdown_limit_pct: float = 20.0
    min_trades: int = 1
    weights: Dict[str, float] = field(default_factory=lambda: {
        "return": 0.35,
        "risk": 0.25,
        "quality": 0.20,
        "validation": 0.20,
    })


@dataclass(slots=True)
class ChallengeSubmission:
    run_id: str
    participant: str
    metrics: Dict[str, Any]
    artifacts: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChallengeScore:
    run_id: str
    participant: str
    total_score: float
    rank: int = 0
    component_scores: Dict[str, float] = field(default_factory=dict)
    disqualified: bool = False
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "run_id": self.run_id,
            "participant": self.participant,
            "total_score": self.total_score,
            "component_scores": self.component_scores,
            "disqualified": self.disqualified,
            "reasons": self.reasons,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }


class ChallengeEvaluator:
    """Scores challenge submissions and produces a reproducible leaderboard."""

    def __init__(self, spec: ChallengeSpec | None = None):
        self.spec = spec or ChallengeSpec()

    def evaluate(self, submissions: Iterable[ChallengeSubmission | Mapping[str, Any]]) -> Dict[str, Any]:
        scores = [self.score_submission(_submission(item)) for item in submissions]
        scores.sort(key=lambda item: (item.disqualified, -item.total_score, item.participant.lower()))
        rank = 1
        for item in scores:
            item.rank = 0 if item.disqualified else rank
            if not item.disqualified:
                rank += 1
        return {
            "challenge": self.spec.name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_submissions": len(scores),
            "qualified_submissions": sum(1 for item in scores if not item.disqualified),
            "leaderboard": [item.to_dict() for item in scores],
        }

    def score_submission(self, submission: ChallengeSubmission) -> ChallengeScore:
        metrics = submission.metrics or {}
        total_return = _metric(metrics, "total_return_pct", "return_pct", "total_return")
        if abs(total_return) <= 1.0 and "total_return_pct" not in metrics and "return_pct" not in metrics:
            total_return *= 100.0
        sharpe = _metric(metrics, "sharpe_ratio", "sharpe")
        sortino = _metric(metrics, "sortino_ratio", "sortino")
        max_drawdown = abs(_metric(metrics, "max_drawdown_pct", "drawdown_pct", "max_drawdown"))
        if 0 < max_drawdown <= 1.0 and "max_drawdown_pct" not in metrics and "drawdown_pct" not in metrics:
            max_drawdown *= 100.0
        trades = int(_metric(metrics, "total_trades", "n_trades", default=0.0))
        p_value = _nested_metric(metrics, ["validation", "p_value"], default=1.0)
        significant = bool(_nested_metric(metrics, ["validation", "significant"], default=False))

        reasons: List[str] = []
        disqualified = False
        if trades < self.spec.min_trades:
            disqualified = True
            reasons.append(f"Requires at least {self.spec.min_trades} trades; got {trades}.")
        if max_drawdown > self.spec.max_drawdown_limit_pct:
            disqualified = True
            reasons.append(
                f"Max drawdown {max_drawdown:.2f}% exceeds limit {self.spec.max_drawdown_limit_pct:.2f}%."
            )

        components = {
            "return": _clamp((total_return + 25.0) / 75.0, 0.0, 1.0) * 100.0,
            "risk": _clamp(1.0 - (max_drawdown / max(self.spec.max_drawdown_limit_pct, 1.0)), 0.0, 1.0) * 100.0,
            "quality": _clamp(((sharpe + max(sortino, sharpe)) / 2.0 + 1.0) / 4.0, 0.0, 1.0) * 100.0,
            "validation": _validation_score(p_value, significant),
        }
        total_score = sum(
            components[name] * self.spec.weights.get(name, 0.0)
            for name in components
        )
        if disqualified:
            total_score = min(total_score, 1.0)

        return ChallengeScore(
            run_id=submission.run_id,
            participant=submission.participant,
            total_score=round(total_score, 3),
            component_scores={k: round(v, 3) for k, v in components.items()},
            disqualified=disqualified,
            reasons=reasons,
            metrics=dict(metrics),
            artifacts=dict(submission.artifacts),
        )

    def export(self, evaluation: Mapping[str, Any], output_dir: str | Path) -> Dict[str, str]:
        """Write leaderboard JSON and CSV artifacts."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / "challenge_leaderboard.json"
        csv_path = out / "challenge_leaderboard.csv"

        json_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

        rows = list(evaluation.get("leaderboard", []))
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "rank", "participant", "run_id", "total_score",
                    "disqualified", "reasons",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "rank": row.get("rank"),
                    "participant": row.get("participant"),
                    "run_id": row.get("run_id"),
                    "total_score": row.get("total_score"),
                    "disqualified": row.get("disqualified"),
                    "reasons": "; ".join(row.get("reasons") or []),
                })

        return {
            "leaderboard_json": str(json_path.resolve()),
            "leaderboard_csv": str(csv_path.resolve()),
        }


def _submission(item: ChallengeSubmission | Mapping[str, Any]) -> ChallengeSubmission:
    if isinstance(item, ChallengeSubmission):
        return item
    return ChallengeSubmission(
        run_id=str(item.get("run_id") or item.get("id") or "unknown"),
        participant=str(item.get("participant") or item.get("agent") or item.get("strategy") or "unknown"),
        metrics=dict(item.get("metrics") or {}),
        artifacts=dict(item.get("artifacts") or {}),
        metadata=dict(item.get("metadata") or {}),
    )


def _metric(metrics: Mapping[str, Any], *names: str, default: float = 0.0) -> float:
    for name in names:
        if name in metrics:
            try:
                return float(metrics[name])
            except (TypeError, ValueError):
                return default
    return default


def _nested_metric(metrics: Mapping[str, Any], path: List[str], default: Any) -> Any:
    node: Any = metrics
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return default
        node = node[key]
    return node


def _validation_score(p_value: float, significant: bool) -> float:
    if significant:
        return 100.0
    try:
        p = float(p_value)
    except (TypeError, ValueError):
        p = 1.0
    return _clamp(1.0 - p, 0.0, 1.0) * 100.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
