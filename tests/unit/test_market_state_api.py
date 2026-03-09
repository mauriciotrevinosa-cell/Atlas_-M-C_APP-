"""
Market-state API contract tests for Atlas server.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from apps.server import server


def _sample_ohlcv(n: int = 80) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(100, 120, n)
    frame = pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.linspace(900_000, 1_200_000, n).astype(int),
        },
        index=dates,
    )
    return frame


def test_market_state_api_returns_expected_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_fetch_ohlcv_local",
        lambda ticker, period="1y": (_sample_ohlcv(90), True),
    )

    payload = server.api_market_state("SPY", period="3mo")

    assert payload["ticker"] == "SPY"
    assert payload["period"] == "3mo"
    assert payload["synthetic"] is True
    assert payload["n_bars"] == 90
    assert set(payload.keys()) == {
        "ticker",
        "period",
        "n_bars",
        "synthetic",
        "regime",
        "volatility",
        "internals",
        "sentiment",
    }
    assert set(payload["regime"].keys()) == {"name", "confidence", "timestamp", "metrics"}
    assert set(payload["volatility"].keys()) == {"regime", "forecast_annualized"}
    assert "score" in payload["sentiment"]
    assert "confidence" in payload["sentiment"]
    assert "source" in payload["sentiment"]
    assert "components" in payload["sentiment"]


def test_market_state_api_requires_minimum_bars(monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "_fetch_ohlcv_local",
        lambda ticker, period="1y": (_sample_ohlcv(10), False),
    )

    with pytest.raises(HTTPException) as exc:
        server.api_market_state("QQQ")

    assert exc.value.status_code == 400
    assert "Need at least 20 bars" in str(exc.value.detail)
