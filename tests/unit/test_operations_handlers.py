from __future__ import annotations

import pytest

from atlas.operations.handlers import portfolio_risk, portfolio_snapshot, signal_snapshot


def test_portfolio_snapshot_uses_only_supplied_prices():
    result = portfolio_snapshot({
        "cash": 100,
        "positions": [{"symbol": "spy", "quantity": 2, "price": 50}],
    }, {})

    assert result["total_value"] == 200
    assert result["positions"][0]["weight"] == 0.5
    assert result["provenance"]["kind"] == "INPUT"


def test_portfolio_snapshot_rejects_missing_price():
    with pytest.raises(ValueError, match="price must be a finite number"):
        portfolio_snapshot({"positions": [{"symbol": "SPY", "quantity": 2}]}, {})


def test_portfolio_risk_reuses_observed_returns():
    result = portfolio_risk({"returns": [0.01, -0.02, 0.005, -0.01]}, {})

    assert result["observations"] == 4
    assert result["historical_var"]["method"] == "historical"
    assert result["provenance"]["kind"] == "COMPUTED"


def test_portfolio_risk_rejects_missing_observations():
    with pytest.raises(ValueError, match="at least two"):
        portfolio_risk({"returns": []}, {})


def test_signal_snapshot_uses_prior_real_step_output():
    result = signal_snapshot({}, {"steps": {"market": {
        "handler": "atlas.market.quick_analysis",
        "data": {"symbol": "SPY", "signal": "bullish", "confidence": 0.67},
    }}})

    assert result["signal"] == "bullish"
    assert result["source_step_id"] == "market"
    assert result["provenance"]["kind"] == "DERIVED"


def test_signal_snapshot_never_invents_missing_signal():
    with pytest.raises(ValueError, match="no prior workflow step"):
        signal_snapshot({}, {"steps": {"portfolio": {"data": {"total": 10}}}})
