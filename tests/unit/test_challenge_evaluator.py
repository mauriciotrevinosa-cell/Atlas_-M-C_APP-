from pathlib import Path

from atlas.evaluation import ChallengeEvaluator, ChallengeSpec, ChallengeSubmission
from atlas.research import ResearchReport, ResearchStage, evaluate_research_reports


def test_challenge_evaluator_ranks_qualified_submissions():
    evaluator = ChallengeEvaluator(
        ChallengeSpec(name="Atlas Eval", max_drawdown_limit_pct=25.0, min_trades=2)
    )
    result = evaluator.evaluate([
        ChallengeSubmission(
            run_id="run-a",
            participant="momentum_agent",
            metrics={
                "total_return_pct": 18.0,
                "sharpe_ratio": 1.4,
                "sortino_ratio": 1.8,
                "max_drawdown_pct": 8.0,
                "total_trades": 12,
                "validation": {"p_value": 0.04, "significant": True},
            },
        ),
        ChallengeSubmission(
            run_id="run-b",
            participant="mean_reversion_agent",
            metrics={
                "total_return_pct": 9.0,
                "sharpe_ratio": 0.8,
                "sortino_ratio": 1.0,
                "max_drawdown_pct": 12.0,
                "total_trades": 10,
                "validation": {"p_value": 0.2, "significant": False},
            },
        ),
    ])

    assert result["challenge"] == "Atlas Eval"
    assert result["qualified_submissions"] == 2
    assert result["leaderboard"][0]["participant"] == "momentum_agent"
    assert result["leaderboard"][0]["rank"] == 1
    assert result["leaderboard"][0]["total_score"] > result["leaderboard"][1]["total_score"]


def test_challenge_evaluator_disqualifies_rule_violations():
    evaluator = ChallengeEvaluator(
        ChallengeSpec(max_drawdown_limit_pct=10.0, min_trades=3)
    )
    result = evaluator.evaluate([
        {
            "run_id": "bad-run",
            "participant": "overfit_strategy",
            "metrics": {
                "total_return_pct": 80.0,
                "sharpe_ratio": 3.0,
                "max_drawdown_pct": 35.0,
                "total_trades": 1,
            },
        }
    ])

    row = result["leaderboard"][0]
    assert row["rank"] == 0
    assert row["disqualified"] is True
    assert row["total_score"] <= 1.0
    assert any("drawdown" in reason.lower() for reason in row["reasons"])
    assert any("trades" in reason.lower() for reason in row["reasons"])


def test_challenge_evaluator_exports_json_and_csv(tmp_path: Path):
    evaluator = ChallengeEvaluator()
    result = evaluator.evaluate([
        {
            "run_id": "run-1",
            "participant": "research_pipeline",
            "metrics": {
                "total_return_pct": 5.0,
                "sharpe_ratio": 0.7,
                "max_drawdown_pct": 4.0,
                "total_trades": 4,
            },
        }
    ])

    artifacts = evaluator.export(result, tmp_path)

    assert Path(artifacts["leaderboard_json"]).exists()
    assert Path(artifacts["leaderboard_csv"]).exists()
    assert "research_pipeline" in Path(artifacts["leaderboard_csv"]).read_text(encoding="utf-8")


def test_research_reports_can_be_scored_as_challenge_submissions():
    report = ResearchReport(
        run_id="research-1",
        generated_at_utc="2026-05-13T00:00:00+00:00",
        stage=ResearchStage.VALIDATION,
        idea_name="Gap Continuation",
        symbols=["SPY"],
        metrics={
            "total_return_pct": 11.0,
            "sharpe_ratio": 1.0,
            "max_drawdown_pct": 6.0,
            "total_trades": 4,
            "validation": {"p_value": 0.03, "significant": True},
        },
        artifacts={"research_report_json": "outputs/runs/research-1/report.json"},
    )

    result = evaluate_research_reports([report], ChallengeSpec(min_trades=2))

    row = result["leaderboard"][0]
    assert row["participant"] == "Gap Continuation"
    assert row["run_id"] == "research-1"
    assert row["rank"] == 1
    assert row["artifacts"]["research_report_json"].endswith("report.json")
