from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from atlas.features import FeatureExpression, FeatureExpressionEngine


@pytest.fixture
def ohlcv():
    return pd.DataFrame(
        {
            "Open": np.linspace(99, 108, 12),
            "High": np.linspace(101, 110, 12),
            "Low": np.linspace(98, 107, 12),
            "Close": np.linspace(100, 111, 12),
            "Volume": np.linspace(1000, 2200, 12),
        }
    )


def test_expression_engine_resolves_columns_case_insensitive(ohlcv):
    engine = FeatureExpressionEngine(ohlcv)

    close = engine.evaluate("$close")

    assert close.iloc[0] == 100
    assert close.iloc[-1] == 111


def test_expression_engine_computes_nested_feature(ohlcv):
    engine = FeatureExpressionEngine(ohlcv)

    feature = engine.evaluate("Div(Sub($close, Mean($close, 3)), Mean($close, 3))")

    expected = (ohlcv["Close"] - ohlcv["Close"].rolling(3, min_periods=3).mean()) / (
        ohlcv["Close"].rolling(3, min_periods=3).mean()
    )
    pd.testing.assert_series_equal(feature, expected, check_names=False)


def test_expression_engine_computes_default_batch(ohlcv):
    engine = FeatureExpressionEngine(ohlcv)

    result = engine.evaluate_many(
        [
            FeatureExpression("ret_1", "Return($close, 1)"),
            FeatureExpression("vol_z_4", "ZScore($volume, 4)"),
            FeatureExpression("corr_4", "Corr($close, $volume, 4)"),
        ]
    )

    assert list(result.columns) == ["ret_1", "vol_z_4", "corr_4"]
    assert result["ret_1"].iloc[-1] == pytest.approx(111 / 110 - 1)
    assert result["corr_4"].dropna().iloc[-1] == pytest.approx(1.0)


def test_expression_engine_rejects_unsupported_expression(ohlcv):
    engine = FeatureExpressionEngine(ohlcv)

    with pytest.raises(ValueError):
        engine.evaluate("__import__('os').system('echo unsafe')")
