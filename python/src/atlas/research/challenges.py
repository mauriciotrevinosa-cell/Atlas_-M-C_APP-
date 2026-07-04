"""Research challenge adapters."""

from __future__ import annotations

from typing import Iterable, Mapping, Any

from atlas.evaluation import ChallengeEvaluator, ChallengeSpec, ChallengeSubmission

from .report import ResearchReport


def evaluate_research_reports(
    reports: Iterable[ResearchReport | Mapping[str, Any]],
    spec: ChallengeSpec | None = None,
) -> dict[str, Any]:
    """Score research reports with the shared Atlas challenge evaluator."""
    submissions = [_report_to_submission(report) for report in reports]
    return ChallengeEvaluator(spec).evaluate(submissions)


def _report_to_submission(report: ResearchReport | Mapping[str, Any]) -> ChallengeSubmission:
    if isinstance(report, ResearchReport):
        return ChallengeSubmission(
            run_id=report.run_id,
            participant=report.idea_name,
            metrics=report.metrics,
            artifacts=report.artifacts,
            metadata={"stage": report.stage.value, "symbols": report.symbols},
        )

    return ChallengeSubmission(
        run_id=str(report.get("run_id") or "unknown"),
        participant=str(report.get("idea_name") or report.get("participant") or "unknown"),
        metrics=dict(report.get("metrics") or {}),
        artifacts=dict(report.get("artifacts") or {}),
        metadata={"stage": report.get("stage"), "symbols": report.get("symbols", [])},
    )
