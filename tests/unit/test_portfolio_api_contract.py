"""
Portfolio API contract tests for Atlas server.
"""

from __future__ import annotations

from apps.server import server


class _DummyScenarioSession:
    def __init__(self) -> None:
        self.capital = 1000.0
        self.positions = {
            "AAPL": {"qty": 2.0, "avg_price": 100.0, "last_price": 120.0},
        }


def test_portfolio_api_without_active_session_returns_explicit_empty_contract() -> None:
    server.scenario_sessions.clear()
    data = server.get_portfolio()

    assert data["source"] == "none"
    assert data["status"] == "unavailable"
    assert data["mode"] == "LIVE"
    assert data["has_active_session"] is False
    assert data["positions"] == []
    assert data["total_equity"] == 0


def test_portfolio_api_with_active_session_returns_scenario_contract() -> None:
    original_sessions = dict(server.scenario_sessions)
    try:
        server.scenario_sessions.clear()
        server.scenario_sessions["test-session"] = _DummyScenarioSession()
        data = server.get_portfolio()
    finally:
        server.scenario_sessions.clear()
        server.scenario_sessions.update(original_sessions)

    assert data["source"] == "scenario"
    assert data["status"] == "live"
    assert data["mode"] == "SIMULATION"
    assert data["has_active_session"] is True
    assert len(data["positions"]) == 1
    assert data["positions"][0]["symbol"] == "AAPL"
    assert data["positions"][0]["qty"] == 2.0
    assert data["positions"][0]["current_price"] == 120.0
    assert data["total_equity"] == 1240.0


def test_portfolio_summary_does_not_invent_a_starting_balance() -> None:
    server.scenario_sessions.clear()
    data = server.get_portfolio_summary()

    assert data["status"] == "unavailable"
    assert data["total_value"] == 0
    assert data["total_pnl"] == 0
    assert data["has_session"] is False
