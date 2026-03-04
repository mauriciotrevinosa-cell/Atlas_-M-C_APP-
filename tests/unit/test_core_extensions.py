from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.core.intraday_patterns import IntradayPatternEngine
from atlas.core.options_probability import OptionsChain, OptionsProbabilityEngine
from atlas.core.signal_discovery import SignalDiscoveryEngine
from atlas.core.system_models import ConstraintEngine, ProbabilisticStateModel, StrategyUtility
from atlas.core.validation import (
    BootstrapTests,
    PBOAnalyzer,
    StrategyScorer,
    WalkForwardAnalyzer,
)
from atlas.core.whale_detection import WhaleDetectionEngine
from atlas.research import PipelineConfig, QuantResearchPipeline, ResearchIdea


def _frame(rows: int = 260, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start="2024-01-01", periods=rows, tz="UTC")
    drift = np.linspace(100.0, 120.0, rows)
    noise = np.cumsum(rng.normal(0.0, 0.9, size=rows))
    close = drift + noise
    open_ = close + rng.normal(0.0, 0.3, size=rows)
    high = np.maximum(open_, close) + np.abs(rng.normal(0.6, 0.2, size=rows))
    low = np.minimum(open_, close) - np.abs(rng.normal(0.6, 0.2, size=rows))
    volume = rng.integers(400_000, 3_000_000, size=rows).astype(float)
    volume[-1] = volume[:-1].mean() * 4.5  # force a likely anomaly

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )
    df.index.name = "timestamp_utc"
    return df


def test_intraday_pattern_engine_outputs_report() -> None:
    engine = IntradayPatternEngine()
    report = engine.analyze(_frame(), symbol="AAPL")
    assert report.symbol == "AAPL"
    assert report.summary["rows"] > 0
    assert len(report.patterns) >= 1


def test_whale_detection_engine_detects_signals() -> None:
    engine = WhaleDetectionEngine()
    report = engine.analyze(_frame(), symbol="MSFT")
    assert report.symbol == "MSFT"
    assert report.summary["rows"] > 0
    assert report.summary["signal_count"] >= 1


def test_signal_discovery_engine_finds_candidates() -> None:
    engine = SignalDiscoveryEngine()
    report = engine.discover(_frame(), max_signals=10, target_horizon=5)
    assert report.generated_at_utc
    assert len(report.signals) > 0


def test_system_models_components() -> None:
    util = StrategyUtility()
    utility = util.evaluate(expected_return=0.12, risk=0.2, cost=0.01, uncertainty=0.05)
    assert isinstance(utility.utility, float)

    constraints = ConstraintEngine()
    violations = constraints.evaluate(
        {
            "leverage": 2.5,
            "turnover": 0.8,
            "liquidity": 500_000,
            "volatility": 0.9,
            "position_concentration": 0.5,
        }
    )
    assert len(violations) >= 1

    state_model = ProbabilisticStateModel()
    dist = state_model.infer({"momentum": 0.4, "volatility": 0.25, "liquidity": 0.5, "stress": 0.2})
    prob_sum = sum(s.probability for s in dist.states)
    assert 0.99 <= prob_sum <= 1.01
    assert dist.most_likely_state in {"bull", "bear", "range", "shock"}


def test_validation_stack_and_scorer() -> None:
    rng = np.random.default_rng(11)
    rows = 400
    strategy_returns = pd.DataFrame(
        {
            "s1": rng.normal(0.0010, 0.01, size=rows),
            "s2": rng.normal(0.0004, 0.01, size=rows),
            "s3": rng.normal(-0.0002, 0.012, size=rows),
        }
    )

    pbo = PBOAnalyzer().analyze(strategy_returns, n_splits=8)
    assert 0.0 <= pbo.pbo <= 1.0
    assert pbo.n_trials > 0

    wf = WalkForwardAnalyzer().analyze(strategy_returns, train_size=180, test_size=60, step_size=40)
    assert wf.n_folds > 0

    boot = BootstrapTests().mean_return_test(strategy_returns["s1"], n_bootstrap=500)
    assert 0.0 <= boot.p_value <= 1.0

    score = StrategyScorer().score(pbo=pbo, walk_forward=wf, bootstrap=boot)
    assert 0.0 <= score.score <= 100.0


def test_options_probability_engine_with_local_chain() -> None:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=35)
    strikes = np.array([90, 95, 100, 105, 110], dtype=float)
    calls = pd.DataFrame(
        {
            "strike": strikes,
            "volume": [120, 160, 210, 175, 130],
            "openInterest": [400, 520, 610, 500, 420],
            "impliedVolatility": [0.28, 0.25, 0.22, 0.24, 0.27],
            "bid": [11, 8, 5, 3, 1.5],
            "ask": [11.5, 8.4, 5.3, 3.2, 1.7],
            "lastPrice": [11.2, 8.1, 5.1, 3.1, 1.6],
            "expiration": [exp] * len(strikes),
            "type": ["call"] * len(strikes),
        }
    )
    puts = calls.copy()
    puts["type"] = "put"
    puts["impliedVolatility"] = [0.30, 0.27, 0.24, 0.26, 0.29]
    chain = OptionsChain(
        symbol="SPY",
        as_of_utc=now.isoformat(),
        underlying_price=100.0,
        calls=calls,
        puts=puts,
    )

    result = OptionsProbabilityEngine().analyze("SPY", chain=chain)
    assert result.symbol == "SPY"
    assert len(result.surface_points) > 0
    prob_sum = sum(result.distribution.probabilities)
    assert 0.99 <= prob_sum <= 1.01


def test_research_pipeline_with_data_override(tmp_path: Path) -> None:
    pipeline = QuantResearchPipeline(config=PipelineConfig(output_root=str(tmp_path / "runs"), n_bootstrap=300))
    idea = ResearchIdea(
        name="Gap Continuation",
        hypothesis="Gap up days continue with elevated probability",
        symbols=["AAPL", "MSFT"],
    )
    report = pipeline.run(
        idea=idea,
        data_override={"AAPL": _frame(seed=2), "MSFT": _frame(seed=3)},
    )
    assert report.run_id
    assert "validation" in report.metrics
    assert Path(report.artifacts["research_report_json"]).exists()

