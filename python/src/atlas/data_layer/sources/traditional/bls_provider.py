"""
Bureau of Labor Statistics public API provider.

Atlas-owned adapter for BLS time series. Version 2 of the public API supports
JSON POST requests and can be used without a key for small requests.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer.bls_provider")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


BLS_SERIES = {
    "UNEMPLOYMENT": "LNS14000000",
    "CPI": "CUUR0000SA0",
    "CORE_CPI": "CUUR0000SA0L1E",
    "PAYROLLS": "CES0000000001",
    "AVERAGE_HOURLY_EARNINGS": "CES0500000003",
    "LABOR_FORCE_PARTICIPATION": "LNS11300000",
}


class BLSProvider:
    """Fetch monthly US labor/inflation series from the BLS API."""

    API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self, session: Optional[Any] = None):
        self.available = REQUESTS_AVAILABLE
        self.api_key = os.environ.get("BLS_API_KEY")
        self.session = session or (requests.Session() if requests else None)

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")

    def get_series(
        self,
        series_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return a BLS series as a DataFrame indexed by monthly date."""
        if not self.available or self.session is None:
            return pd.DataFrame()

        resolved_id = BLS_SERIES.get(series_id.upper(), series_id)
        body: Dict[str, Any] = {"seriesid": [resolved_id]}
        start_year = self._year(start)
        end_year = self._year(end)
        if start_year:
            body["startyear"] = start_year
        if end_year:
            body["endyear"] = end_year
        if self.api_key:
            body["registrationkey"] = self.api_key

        try:
            response = self.session.post(self.API_URL, json=body, timeout=15)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "REQUEST_SUCCEEDED":
                logger.warning("BLS request failed for %s: %s", resolved_id, payload)
                return pd.DataFrame()

            series = payload.get("Results", {}).get("series", [])
            points = series[0].get("data", []) if series else []
            records = []
            for item in points:
                period = item.get("period", "")
                year = item.get("year")
                value = item.get("value")
                if not year or not period.startswith("M") or period == "M13" or value is None:
                    continue
                month = int(period[1:])
                records.append(
                    {
                        "date": pd.Timestamp(year=int(year), month=month, day=1),
                        "value": float(str(value).replace(",", "")),
                        "series_id": resolved_id,
                        "provider": "BLS",
                    }
                )

            if not records:
                return pd.DataFrame()

            return pd.DataFrame(records).set_index("date").sort_index()
        except Exception as exc:
            logger.warning("BLS request failed for %s: %s", resolved_id, exc)
            return pd.DataFrame()

    def list_series(self) -> Dict[str, str]:
        return BLS_SERIES.copy()

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "BLS",
            "available": self.available,
            "api_key_required": False,
            "api_key_set": bool(self.api_key),
            "series_count": len(BLS_SERIES),
        }

    @staticmethod
    def _year(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return str(value)[:4]
