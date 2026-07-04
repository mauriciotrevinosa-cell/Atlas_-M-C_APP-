"""
U.S. Treasury Fiscal Data API provider.

Atlas-owned adapter for selected Treasury FiscalData endpoints. No API key is
required for the public datasets used here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer.treasury_provider")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


TREASURY_SERIES = {
    "PUBLIC_DEBT": {
        "endpoint": "v2/accounting/od/debt_to_penny",
        "date_field": "record_date",
        "value_field": "tot_pub_debt_out_amt",
    },
    "OPERATING_CASH_BALANCE": {
        "endpoint": "v1/accounting/dts/dts_table_1",
        "date_field": "record_date",
        "value_field": "account_close_today_bal",
        "filter": "account_type:eq:Treasury General Account (TGA) Closing Balance",
    },
}


class TreasuryFiscalProvider:
    """Fetch selected macro/fiscal time series from FiscalData Treasury."""

    BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

    def __init__(self, session: Optional[Any] = None):
        self.available = REQUESTS_AVAILABLE
        self.session = session or (requests.Session() if requests else None)

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")

    def get_series(
        self,
        series_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return a supported Treasury fiscal series as a DataFrame."""
        if not self.available or self.session is None:
            return pd.DataFrame()

        spec = TREASURY_SERIES.get(series_id.upper())
        if not spec:
            return pd.DataFrame()

        params: Dict[str, Any] = {
            "fields": f"{spec['date_field']},{spec['value_field']}",
            "sort": f"-{spec['date_field']}",
            "page[size]": 5000,
        }

        filters = []
        if start:
            filters.append(f"{spec['date_field']}:gte:{start}")
        if end:
            filters.append(f"{spec['date_field']}:lte:{end}")
        if spec.get("filter"):
            filters.append(str(spec["filter"]))
        if filters:
            params["filter"] = ",".join(filters)

        url = f"{self.BASE_URL}/{spec['endpoint']}"

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            records = []
            for item in payload.get("data", []):
                raw_value = item.get(spec["value_field"])
                raw_date = item.get(spec["date_field"])
                if raw_value in (None, "") or not raw_date:
                    continue
                records.append(
                    {
                        "date": pd.Timestamp(raw_date),
                        "value": float(str(raw_value).replace(",", "")),
                        "series_id": series_id.upper(),
                        "provider": "TreasuryFiscal",
                    }
                )

            if not records:
                return pd.DataFrame()

            return pd.DataFrame(records).set_index("date").sort_index()
        except Exception as exc:
            logger.warning("Treasury request failed for %s: %s", series_id, exc)
            return pd.DataFrame()

    def list_series(self) -> Dict[str, str]:
        return {key: value["endpoint"] for key, value in TREASURY_SERIES.items()}

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "TreasuryFiscal",
            "available": self.available,
            "api_key_required": False,
            "series_count": len(TREASURY_SERIES),
        }
