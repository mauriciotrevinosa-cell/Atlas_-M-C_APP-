from __future__ import annotations

import pytest

from apps.server import server
from atlas.lab.quantum import QuantumPortfolioQUBO


def test_quantum_portfolio_qubo_selects_best_binary_state() -> None:
    optimizer = QuantumPortfolioQUBO()

    result = optimizer.optimize(
        assets=["AAPL", "MSFT", "TLT"],
        expected_returns=[0.12, 0.10, 0.04],
        covariance=[
            [0.040, 0.018, 0.002],
            [0.018, 0.030, 0.001],
            [0.002, 0.001, 0.010],
        ],
        cardinality=2,
        risk_aversion=1.0,
    )

    assert result.bitstring in {"101", "011", "110"}
    assert len(result.selected_assets) == 2
    assert result.to_dict()["ontology"] == "mau_market_ontology"
    assert result.to_dict()["atlas_layer"] == "mmo"


def test_mmo_quantum_portfolio_endpoint_returns_read_only_contract() -> None:
    payload = server.mmo_quantum_portfolio(
        server.MMOQuantumPortfolioRequest(
            assets=["AAPL", "MSFT", "TLT"],
            expected_returns=[0.12, 0.10, 0.04],
            covariance=[
                [0.040, 0.018, 0.002],
                [0.018, 0.030, 0.001],
                [0.002, 0.001, 0.010],
            ],
            cardinality=2,
            risk_aversion=1.0,
        )
    )

    assert payload["module"] == "mmo_quantum_portfolio"
    assert payload["ontology"] == "mau_market_ontology"
    assert payload["read_only"] is True
    assert payload["trading_supported"] is False
    assert payload["result"]["atlas_layer"] == "mmo"


def test_mmo_quantum_portfolio_rejects_bad_cardinality() -> None:
    with pytest.raises(server.HTTPException) as exc_info:
        server.mmo_quantum_portfolio(
            server.MMOQuantumPortfolioRequest(
                assets=["AAPL"],
                expected_returns=[0.12],
                covariance=[[0.04]],
                cardinality=2,
            )
        )

    assert exc_info.value.status_code == 400
