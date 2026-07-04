from __future__ import annotations

import numpy as np
import pandas as pd

from atlas.market_state import MarketStateToken, MarketStateTokenizer


def _ohlcv(rows=260):
    dates = pd.date_range("2025-01-01", periods=rows)
    close = np.linspace(100, 260, rows)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.linspace(1_000, 2_000, rows),
        },
        index=dates,
    )


def test_market_state_token_serializes():
    token = MarketStateToken("regime", "trending_up", 0.8, "unit")

    assert token.token == "REGIME:TRENDING_UP"
    assert token.to_dict()["score"] == 0.8


def test_market_state_tokenizer_from_ohlcv():
    tokenizer = MarketStateTokenizer()

    tokens = tokenizer.from_ohlcv(_ohlcv(), ticker="SPY")
    rendered = tokenizer.to_prompt_context(tokens)

    token_values = {token.token for token in tokens}
    assert "ASSET:SPY" in token_values
    assert any(token.startswith("REGIME:") for token in token_values)
    assert any(token.startswith("VOLATILITY:") for token in token_values)
    assert "MOMENTUM_5:UP" in token_values
    assert "MOMENTUM_20:UP" in token_values
    assert "ASSET:SPY" in rendered


def test_market_state_tokenizer_handles_short_data():
    tokenizer = MarketStateTokenizer()

    tokens = tokenizer.from_ohlcv(_ohlcv(rows=10), ticker="BTC")

    token_values = {token.token for token in tokens}
    assert "REGIME:UNKNOWN" in token_values
    assert "VOLATILITY:UNKNOWN" in token_values
