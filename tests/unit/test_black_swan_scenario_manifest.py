from __future__ import annotations

from atlas.black_swan import ScenarioEngine


def test_scenario_report_includes_run_manifest():
    engine = ScenarioEngine()

    report = engine.run_all(
        asset_names=["SPY", "GLD"],
        weights=[0.8, 0.2],
        betas={"SPY": 1.0, "GLD": -0.1},
        sectors={"SPY": "BROAD", "GLD": "GOLD"},
        categories=["HYPOTHETICAL"],
    )
    payload = report.to_dict()

    assert payload["manifest"]["schema"] == "atlas.black_swan.scenario_run.v1"
    assert payload["manifest"]["weights"] == {"SPY": 0.8, "GLD": 0.2}
    assert payload["manifest"]["categories"] == ["HYPOTHETICAL"]
    assert payload["manifest"]["beta_count"] == 2
    assert payload["manifest"]["sector_count"] == 2
    assert len(payload["manifest"]["scenario_names"]) == report.n_scenarios
