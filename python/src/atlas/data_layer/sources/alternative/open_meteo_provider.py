"""
Open-Meteo weather context provider.

Atlas-owned adapter for no-key weather context useful for commodities,
agriculture, energy, logistics, and regional risk analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer.open_meteo_provider")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


class OpenMeteoProvider:
    """Fetch forecast or archive weather data from Open-Meteo."""

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    DEFAULT_DAILY = [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "windspeed_10m_max",
    ]

    def __init__(self, session: Optional[Any] = None):
        self.available = REQUESTS_AVAILABLE
        self.session = session or (requests.Session() if requests else None)

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")

    def get_weather(
        self,
        latitude: float,
        longitude: float,
        start: Optional[str] = None,
        end: Optional[str] = None,
        variables: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Return daily weather context indexed by date."""
        if not self.available or self.session is None:
            return pd.DataFrame()

        use_archive = bool(start and end)
        url = self.ARCHIVE_URL if use_archive else self.FORECAST_URL
        params: Dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join(variables or self.DEFAULT_DAILY),
            "timezone": "UTC",
        }
        if start:
            params["start_date"] = start
        if end:
            params["end_date"] = end

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            daily = payload.get("daily", {})
            dates = daily.get("time", [])
            if not dates:
                return pd.DataFrame()

            frame_data: Dict[str, Any] = {"date": pd.to_datetime(dates)}
            for key, values in daily.items():
                if key == "time":
                    continue
                frame_data[key] = values

            frame = pd.DataFrame(frame_data).set_index("date").sort_index()
            frame["latitude"] = float(payload.get("latitude", latitude))
            frame["longitude"] = float(payload.get("longitude", longitude))
            frame["provider"] = "OpenMeteo"
            return frame
        except Exception as exc:
            logger.warning("Open-Meteo request failed for %s,%s: %s", latitude, longitude, exc)
            return pd.DataFrame()

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "OpenMeteo",
            "available": self.available,
            "api_key_required": False,
            "series_count": len(self.DEFAULT_DAILY),
            "context": "weather",
        }
