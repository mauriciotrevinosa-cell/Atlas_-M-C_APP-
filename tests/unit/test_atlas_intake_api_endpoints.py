from __future__ import annotations

import pandas as pd

from apps.server import server


class FakeRegistry:
    def get_macro(self, series_id: str, start=None, end=None):
        return pd.DataFrame(
            [{"value": 2.8, "provider": "IMFDataMapper", "series_id": series_id}],
            index=[pd.Timestamp("2024-01-01")],
        )

    def get_weather(self, latitude: float, longitude: float, start=None, end=None):
        return pd.DataFrame(
            [{"temperature_2m_max": 31.5, "provider": "OpenMeteo"}],
            index=[pd.Timestamp("2026-05-12")],
        )


class FakePolymarketProvider:
    def search_markets(self, query=None, limit=20):
        return [
            {
                "provider": "PolymarketGamma",
                "question": "Will CPI be above consensus?",
                "probabilities": {"Yes": 0.62, "No": 0.38},
                "read_only": True,
            }
        ]

    def find_market(self, identifier, outcome=None):
        return {
            "provider": "PolymarketGamma",
            "market_id": "123",
            "condition_id": "0xabc",
            "slug": "cpi-above-consensus",
            "question": "Will CPI be above consensus?",
            "selected_outcome": {
                "outcome": outcome or "Yes",
                "token_id": "token-yes",
                "probability": 0.62,
            },
            "read_only": True,
        }


def test_macro_series_endpoint_returns_registry_records(monkeypatch) -> None:
    monkeypatch.setattr(server, "get_provider_registry", lambda: FakeRegistry())

    payload = server.macro_series("GDP_REAL_GROWTH", start="2024-01-01", end="2024-12-31")

    assert payload["status"] == "ok"
    assert payload["records"][0]["provider"] == "IMFDataMapper"
    assert payload["records"][0]["date"] == "2024-01-01T00:00:00"


def test_weather_context_endpoint_returns_registry_records(monkeypatch) -> None:
    monkeypatch.setattr(server, "get_provider_registry", lambda: FakeRegistry())

    payload = server.weather_context(25.76, -80.19, start="2026-05-12", end="2026-05-12")

    assert payload["status"] == "ok"
    assert payload["records"][0]["provider"] == "OpenMeteo"
    assert payload["records"][0]["temperature_2m_max"] == 31.5


def test_prediction_markets_endpoint_is_read_only(monkeypatch) -> None:
    import atlas.data_layer.sources.prediction as prediction

    monkeypatch.setattr(prediction, "PolymarketGammaProvider", lambda: FakePolymarketProvider())

    payload = server.prediction_markets(query="CPI", limit=5)

    assert payload["mode"] == "read_only"
    assert payload["trading_supported"] is False
    assert payload["markets"][0]["read_only"] is True


def test_prediction_resolve_endpoint_is_read_only(monkeypatch) -> None:
    import atlas.data_layer.sources.prediction as prediction

    monkeypatch.setattr(prediction, "PolymarketGammaProvider", lambda: FakePolymarketProvider())

    payload = server.prediction_resolve(identifier="cpi-above-consensus", outcome="Yes")

    assert payload["mode"] == "read_only"
    assert payload["trading_supported"] is False
    assert payload["market"]["selected_outcome"]["probability"] == 0.62


def test_evaluation_challenge_score_endpoint_is_read_only() -> None:
    req = server.ChallengeScoreRequest(
        challenge_name="Endpoint Challenge",
        max_drawdown_limit_pct=20,
        min_trades=2,
        submissions=[
            server.ChallengeSubmissionRequest(
                run_id="run-good",
                participant="agent_good",
                metrics={
                    "total_return_pct": 16,
                    "sharpe_ratio": 1.2,
                    "sortino_ratio": 1.5,
                    "max_drawdown_pct": 7,
                    "total_trades": 5,
                },
            ),
            server.ChallengeSubmissionRequest(
                run_id="run-bad",
                participant="agent_bad",
                metrics={
                    "total_return_pct": 80,
                    "sharpe_ratio": 3.0,
                    "max_drawdown_pct": 35,
                    "total_trades": 1,
                },
            ),
        ],
    )

    payload = server.evaluation_challenge_score(req)

    assert payload["status"] == "ok"
    assert payload["read_only"] is True
    assert payload["trading_supported"] is False
    board = payload["result"]["leaderboard"]
    assert board[0]["participant"] == "agent_good"
    assert board[0]["rank"] == 1
    assert board[-1]["disqualified"] is True
