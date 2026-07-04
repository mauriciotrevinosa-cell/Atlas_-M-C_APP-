"""
IMF DataMapper API provider.

Atlas-owned adapter for the official IMF DataMapper API. It provides no-key
country macro series such as real GDP growth, inflation, unemployment, and debt.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer.imf_provider")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


IMF_DATAMAPPER_SERIES = {
    "GDP_REAL_GROWTH": "NGDP_RPCH",
    "GDP_NOMINAL": "NGDPD",
    "INFLATION": "PCPIPCH",
    "UNEMPLOYMENT": "LUR",
    "CURRENT_ACCOUNT": "BCA_NGDPD",
    "GOV_DEBT": "GGXWDG_NGDP",
}


class IMFDataMapperProvider:
    """Fetch annual country macro series from IMF DataMapper."""

    BASE_URL = "https://www.imf.org/external/datamapper/api/v2"

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
        """Return an IMF DataMapper series as a DataFrame indexed by year."""
        if not self.available or self.session is None:
            return pd.DataFrame()

        indicator = IMF_DATAMAPPER_SERIES.get(series_id.upper(), series_id)
        country_code = country or self.country
        params = {}
        periods = self._periods(start, end)
        if periods:
            params["periods"] = periods

        try:
            response = self.session.get(
                f"{self.BASE_URL}/{indicator}/{country_code}",
                params=params,
                headers={"User-Agent": "Atlas Data Layer"},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            values = self._extract_values(payload, indicator, country_code)
            records = [
                {
                    "date": pd.Timestamp(f"{year}-01-01"),
                    "value": float(value),
                    "series_id": indicator,
                    "country": country_code,
                    "provider": "IMFDataMapper",
                }
                for year, value in values.items()
                if value is not None
            ]
            if not records:
                return pd.DataFrame()
            return pd.DataFrame(records).set_index("date").sort_index()
        except Exception as exc:
            logger.warning("IMF DataMapper request failed for %s/%s: %s", indicator, country_code, exc)
            return pd.DataFrame()

    def list_series(self) -> Dict[str, str]:
        return IMF_DATAMAPPER_SERIES.copy()

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "IMFDataMapper",
            "available": self.available,
            "api_key_required": False,
            "series_count": len(IMF_DATAMAPPER_SERIES),
            "default_country": self.country,
        }

    @staticmethod
    def _periods(start: Optional[str], end: Optional[str]) -> Optional[str]:
        start_year = str(start)[:4] if start else None
        end_year = str(end)[:4] if end else None
        if not start_year and not end_year:
            return None
        if start_year and end_year:
            return ",".join(str(year) for year in range(int(start_year), int(end_year) + 1))
        return start_year or end_year

    @staticmethod
    def _extract_values(payload: Dict[str, Any], indicator: str, country: str) -> Dict[str, Any]:
        values = payload.get("values", {})
        if isinstance(values, dict):
            indicator_node = values.get(indicator, values)
            if isinstance(indicator_node, dict):
                country_node = indicator_node.get(country, indicator_node)
                if isinstance(country_node, dict):
                    return country_node
        return {}
