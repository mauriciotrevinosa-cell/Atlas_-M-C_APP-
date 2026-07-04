"""
World Bank Indicators API provider.

Atlas-owned adapter inspired by the public API intake backlog. Uses the
official World Bank Indicators API and does not require an API key.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer.worldbank_provider")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


WORLD_BANK_SERIES = {
    "GDP": "NY.GDP.MKTP.CD",
    "GDP_REAL_GROWTH": "NY.GDP.MKTP.KD.ZG",
    "CPI": "FP.CPI.TOTL",
    "INFLATION": "FP.CPI.TOTL.ZG",
    "UNEMPLOYMENT": "SL.UEM.TOTL.ZS",
    "POPULATION": "SP.POP.TOTL",
    "CURRENT_ACCOUNT": "BN.CAB.XOKA.CD",
}


class WorldBankProvider:
    """Fetch annual macro indicators from the World Bank API."""

    BASE_URL = "https://api.worldbank.org/v2"

    def __init__(self, session: Optional[Any] = None, country: str = "USA"):
        self.available = REQUESTS_AVAILABLE
        self.country = country
        self.session = session or (requests.Session() if requests else None)

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")

    def get_series(
        self,
        series_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        country: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return a World Bank indicator as a DataFrame indexed by date."""
        if not self.available or self.session is None:
            return pd.DataFrame()

        indicator = WORLD_BANK_SERIES.get(series_id.upper(), series_id)
        params: Dict[str, Any] = {"format": "json", "per_page": 20000}

        start_year = self._year(start)
        end_year = self._year(end)
        if start_year or end_year:
            params["date"] = f"{start_year or ''}:{end_year or ''}"

        url = f"{self.BASE_URL}/country/{country or self.country}/indicator/{indicator}"

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            records = []
            for item in rows or []:
                value = item.get("value")
                year = item.get("date")
                if value is None or not year:
                    continue
                records.append(
                    {
                        "date": pd.Timestamp(f"{year}-01-01"),
                        "value": float(value),
                        "series_id": indicator,
                        "country": item.get("countryiso3code") or country or self.country,
                        "provider": "WorldBank",
                    }
                )

            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records).set_index("date").sort_index()
            return df
        except Exception as exc:
            logger.warning("World Bank request failed for %s: %s", indicator, exc)
            return pd.DataFrame()

    def list_series(self) -> Dict[str, str]:
        return WORLD_BANK_SERIES.copy()

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "WorldBank",
            "available": self.available,
            "api_key_required": False,
            "series_count": len(WORLD_BANK_SERIES),
            "default_country": self.country,
        }

    @staticmethod
    def _year(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return str(value)[:4]
