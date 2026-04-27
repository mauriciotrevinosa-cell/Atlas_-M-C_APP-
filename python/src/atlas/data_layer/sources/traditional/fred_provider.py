"""
Federal Reserve Economic Data (FRED) API Provider

Fetches macroeconomic data from the St. Louis Federal Reserve.
Uses fredapi library for easy access to FRED series.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from typing import Optional, List, Dict

import pandas as pd

logger = logging.getLogger("atlas.data_layer.fred_provider")

try:
    from fredapi import Fred
    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False


# Common FRED series IDs
FRED_SERIES = {
    "GDP": "A191RL1Q225SBEA",  # Real GDP
    "CPI": "CPIAUCSL",  # Consumer Price Index
    "UNEMPLOYMENT": "UNRATE",  # Unemployment Rate
    "FED_FUNDS": "FEDFUNDS",  # Effective Federal Funds Rate
    "T10Y2Y": "T10Y2Y",  # 10-Year minus 2-Year Treasury Spread
    "T10Y3M": "T10Y3M",  # 10-Year minus 3-Month Treasury Spread
    "INFLATION": "PCEPI",  # Personal Consumption Expenditures Price Index
    "INDUSTRIAL_PRODUCTION": "INDPRO",  # Industrial Production Index
    "RETAIL_SALES": "RSXFS",  # Retail and Food Services Sales
    "DEXUSEU": "DEXUSEU",  # USD/EUR Exchange Rate
    "VIXCLS": "VIXCLS",  # VIX Volatility Index
    "DGS10": "DGS10",  # 10-Year Treasury Constant Maturity Rate
    "DGS2": "DGS2",  # 2-Year Treasury Constant Maturity Rate
    "MORTGAGE30US": "MORTGAGE30US",  # 30-Year Fixed Rate Mortgage Average
}


class FREDProvider:
    """
    Fetches macroeconomic data from Federal Reserve Economic Data (FRED).

    Requires FRED_API_KEY environment variable.

    Example::

        provider = FREDProvider()
        if provider.available:
            gdp = provider.get_series("GDP", "2020-01-01", "2024-12-31")
            multi = provider.get_multiple_series(["GDP", "CPI"], "2020-01-01", "2024-12-31")
    """

    def __init__(self):
        """Initialize FRED provider with API key from environment"""
        self.available = False
        self.api_key = os.environ.get("FRED_API_KEY")

        if not self.api_key:
            logger.warning("FRED_API_KEY not found in environment")
            return

        if not FREDAPI_AVAILABLE:
            logger.warning("fredapi not installed. Install with: pip install fredapi")
            return

        try:
            self.client = Fred(api_key=self.api_key)
            self.available = True
            logger.info("FRED provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FRED client: {e}")

    def get_series(
        self,
        series_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get a single FRED series.

        Args:
            series_id: FRED series ID (e.g., "GDP", "UNRATE", or full ID like "A191RL1Q225SBEA")
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format

        Returns:
            DataFrame with columns ['value'] and DatetimeIndex.
            Returns empty DataFrame on failure.

        Example::

            df = provider.get_series("GDP", "2020-01-01", "2024-12-31")
            # Returns:
            #             value
            # 2020-01-01 21531.0
            # 2020-04-01 21170.3
            # ...
        """
        if not self.available:
            logger.warning("FRED provider not available (no API key or library)")
            return pd.DataFrame()

        try:
            # Resolve series name to ID
            series_id = FRED_SERIES.get(series_id.upper(), series_id)

            # Fetch data
            series = self.client.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )

            if series.empty:
                logger.warning(f"No data returned for FRED series {series_id}")
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame({"value": series})
            df.index.name = "date"

            logger.info(
                f"Got {len(df)} observations for FRED series {series_id} "
                f"({start} to {end})"
            )
            return df

        except Exception as e:
            logger.error(f"Failed to fetch FRED series {series_id}: {e}")
            return pd.DataFrame()

    def get_multiple_series(
        self,
        series_ids: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get multiple FRED series at once.

        Args:
            series_ids: List of FRED series IDs or common names (GDP, CPI, UNEMPLOYMENT, etc.)
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format

        Returns:
            DataFrame with columns for each series.
            Returns empty DataFrame on failure.

        Example::

            df = provider.get_multiple_series(
                ["GDP", "UNEMPLOYMENT", "CPI"],
                "2020-01-01",
                "2024-12-31"
            )
            # Returns:
            #             GDP  UNEMPLOYMENT  CPI
            # 2020-01-01 21531.0  3.5        256.394
            # ...
        """
        if not self.available:
            logger.warning("FRED provider not available")
            return pd.DataFrame()

        try:
            data = {}

            for series_id in series_ids:
                try:
                    # Resolve common names to FRED IDs
                    resolved_id = FRED_SERIES.get(series_id.upper(), series_id)

                    # Fetch series
                    series = self.client.get_series(
                        resolved_id,
                        observation_start=start,
                        observation_end=end,
                    )

                    if not series.empty:
                        # Use original name or ID as column
                        col_name = series_id.upper()
                        data[col_name] = series

                except Exception as e:
                    logger.warning(f"Failed to fetch FRED series {series_id}: {e}")

            if not data:
                logger.warning(f"No data returned for any of {series_ids}")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df.index.name = "date"

            logger.info(
                f"Got {len(df)} observations for {len(data)} FRED series "
                f"({start} to {end})"
            )
            return df

        except Exception as e:
            logger.error(f"Failed to fetch multiple FRED series: {e}")
            return pd.DataFrame()

    def list_series(self) -> Dict[str, str]:
        """
        Get list of common FRED series identifiers.

        Returns:
            Dict mapping series names to FRED IDs
        """
        return FRED_SERIES.copy()

    def get_info(self) -> Dict[str, any]:
        """Get provider information"""
        return {
            "name": "FRED",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "library_available": FREDAPI_AVAILABLE,
            "series_count": len(FRED_SERIES),
        }
