from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from atlas.market_finance.analytics_layer import AnalyticsEngine
from atlas.market_finance.data_layer import DataPayload, DataRouter
from atlas.market_finance.pipeline import Phase1Workflow
from atlas.market_finance.risk_layer import RiskConfig, RiskEngine
from atlas.market_finance.simulation_layer import SimulationConfig, SimulationEngine


def make_frame(rows: int = 260, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=rows, tz="UTC")
    rng = np.random.default_rng(7)
    base = 100 + np.cumsum(rng.normal(0.1, 1.2, size=rows))

    frame = pd.DataFrame(
        {
            "open": base + rng.normal(0.0, 0.4, size=rows),
            "high": base + np.abs(rng.normal(0.8, 0.4, size=rows)),
            "low": base - np.abs(rng.normal(0.8, 0.4, size=rows)),
            "close": base,
            "volume": rng.integers(500_000, 4_500_000, size=rows),
        },
        index=idx,
    )
    frame.index.name = "timestamp_utc"
    return frame


def test_data_router_cache_hit_without_network(tmp_path: Path) -> None:
    router = DataRouter(provider_priority=["invalid_provider"], cache_dir=str(tmp_path / "cache"))

    symbol = "AAPL"
    start = "2024-01-01"
    end = "2024-12-31"
    interval = "1d"
    key = f"phase1_{symbol}_{start}_{end}_{interval}"

    frame = make_frame(rows=80, start=start)
    router.cache.set(key, frame)

    payload = router.get_data(
        symbol=symbol,
        start_date=start,
        end_date=end,
        interval=interval,
        run_dir=tmp_path / "run",
    )

    assert payload.cache_hit is True
    assert payload.source == "cache"
    assert payload.metadata["pit"]["version"] == "v1"
    assert Path(payload.files["dataset_csv"]).exists()


def test_analytics_simulation_risk_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    market_data = {
        "AAPL": make_frame(rows=260, start="2024-01-01"),
        "MSFT": make_frame(rows=260, start="2024-01-01") * [1, 1, 1, 1.03, 1],
    }

    analytics = AnalyticsEngine().analyze(market_data, run_dir=run_dir)
    assert "analytics_report_json" in analytics.files
    assert Path(analytics.files["correlation_heatmap_png"]).exists()

    simulation = SimulationEngine().simulate(
        analytics.enriched_frames,
        run_dir=run_dir,
        config=SimulationConfig(n_paths=300, horizon_days=60, seed=12),
    )
    assert Path(simulation.files["portfolio_histogram_png"]).exists()

    risk = RiskEngine().evaluate(
        analytics.enriched_frames,
        simulation_result=simulation,
        run_dir=run_dir,
        config=RiskConfig(confidence=0.95, loss_threshold=0.05),
    )
    assert Path(risk.files["risk_report_json"]).exists()
    assert "portfolio" in risk.report


def test_phase1_workflow_end_to_end_with_stubbed_data(tmp_path: Path) -> None:
    workflow = Phase1Workflow(output_root=str(tmp_path / "runs"))

    def fake_get_many(
        symbols,
        start_date,
        end_date,
        interval,
        as_of,
        run_dir,
        use_cache,
        allow_stale_cache,
    ):
        payloads = {}
        for symbol in symbols:
            frame = make_frame(rows=220, start="2024-01-01")
            payloads[symbol] = DataPayload(
                symbol=symbol,
                frame=frame,
                metadata={"symbol": symbol, "pit": {"version": "v1", "dataset_hash": "stub"}},
                cache_key=f"stub_{symbol}",
                cache_hit=False,
                source="stub",
                files={},
            )
        return payloads

    workflow.data_router.get_many = fake_get_many  # type: ignore[assignment]

    summary = workflow.run(
        symbols=["AAPL", "MSFT", "SPY"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        n_paths=200,
        horizon_days=45,
    )

    assert Path(summary.manifest_path).exists()
    assert summary.key_metrics["portfolio_var"] >= 0.0
    assert summary.key_metrics["portfolio_cvar"] >= 0.0
