from __future__ import annotations

from atlas.data_layer.provider_registry import DataProviderRegistry
from atlas.data_layer.sources.alternative import OpenMeteoProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeOpenMeteoSession:
    def get(self, url, params=None, timeout=15):
        assert "open-meteo.com" in url
        assert params["latitude"] == 25.76
        assert params["longitude"] == -80.19
        return FakeResponse(
            {
                "latitude": 25.76,
                "longitude": -80.19,
                "daily": {
                    "time": ["2026-05-12"],
                    "temperature_2m_max": [31.5],
                    "temperature_2m_min": [24.2],
                    "precipitation_sum": [3.1],
                    "windspeed_10m_max": [18.0],
                },
            }
        )


def test_open_meteo_provider_parses_daily_weather_payload() -> None:
    provider = OpenMeteoProvider(session=FakeOpenMeteoSession())

    frame = provider.get_weather(25.76, -80.19, start="2026-05-12", end="2026-05-12")

    assert not frame.empty
    assert frame.iloc[0]["temperature_2m_max"] == 31.5
    assert frame.iloc[0]["provider"] == "OpenMeteo"


def test_default_registry_includes_weather_channel() -> None:
    registry = DataProviderRegistry()
    info = registry.get_provider_info()

    assert "weather" in info
    assert {item["name"] for item in info["weather"]} == {"OpenMeteo"}
