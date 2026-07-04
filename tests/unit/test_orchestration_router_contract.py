import pandas as pd

from atlas.orchestration.router import AnalysisRequest, PipelineRouter


def test_pipeline_router_uses_data_manager_historical_contract():
    index = pd.date_range("2026-01-01", periods=80, freq="D")
    frame = pd.DataFrame({
        "open": range(100, 180),
        "high": range(101, 181),
        "low": range(99, 179),
        "close": range(100, 180),
        "volume": [1000] * 80,
    }, index=index)

    class Manager:
        def get_historical(self, **kwargs):
            assert kwargs["symbol"] == "SPY"
            assert kwargs["timeframe"] == "3mo"
            return frame

    router = PipelineRouter()
    router._data_manager = Manager()
    result = router.run(AnalysisRequest(symbol="SPY", timeframe="3mo", modules=["indicators"]))

    assert result.indicators["current_price"] == 179
    assert not result.errors
