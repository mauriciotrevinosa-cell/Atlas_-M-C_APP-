"""
SEC EDGAR Data Provider

Fetches SEC filings, company facts, and submission data from the EDGAR database.
No API key required; just needs User-Agent header.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
import time
from typing import Optional, Dict, List, Any

logger = logging.getLogger("atlas.data_layer.sec_edgar_provider")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# Common ticker to CIK mapping (partial; can be expanded)
TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "META": "0001326801",
    "TSLA": "0001318605",
    "JPM": "0000019617",
    "V": "0001403161",
    "WMT": "0000104169",
    "MA": "0001141391",
}


class SECEDGARProvider:
    """
    Fetches SEC filings and company data from the EDGAR database.

    No API key required; uses SEC's public API with User-Agent header.
    Respects 10 requests/second rate limit.

    Example::

        provider = SECEDGARProvider()
        filings = provider.get_filings("AAPL", "10-K", count=5)
        facts = provider.get_company_facts("AAPL")
        subs = provider.get_submissions("0000320193")
    """

    BASE_URL = "https://data.sec.gov/api/xbrl"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"

    def __init__(self):
        """Initialize SEC EDGAR provider"""
        self.available = REQUESTS_AVAILABLE
        self.user_agent = os.environ.get(
            "SEC_EDGAR_USER_AGENT",
            "Mozilla/5.0 (Atlas Data Layer; +https://atlas.local)",
        )
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 10 requests/second limit

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")
            return

        logger.info("SEC EDGAR provider initialized")

    def _respect_rate_limit(self) -> None:
        """Wait to respect 10 requests/second rate limit"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Make authenticated request to SEC API.

        Args:
            url: Full URL
            params: Query parameters

        Returns:
            JSON response or None on failure
        """
        self._respect_rate_limit()

        try:
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SEC API request failed: {e}")
            return None

    def ticker_to_cik(self, ticker: str) -> str:
        """
        Convert ticker symbol to CIK number.

        Args:
            ticker: Stock ticker (e.g., "AAPL")

        Returns:
            CIK number as zero-padded string (e.g., "0000320193")
            Returns empty string if not found.
        """
        ticker_upper = ticker.upper()

        # Check cache
        if ticker_upper in TICKER_TO_CIK:
            return TICKER_TO_CIK[ticker_upper]

        # Try to fetch from SEC
        try:
            data = self._make_request(
                "https://www.sec.gov/files/company_tickers.json"
            )

            if data:
                for entry in data.values():
                    if entry.get("ticker", "").upper() == ticker_upper:
                        cik = entry.get("cik_str")
                        return f"{cik:010d}"

            logger.warning(f"Could not find CIK for ticker {ticker}")
            return ""

        except Exception as e:
            logger.warning(f"Failed to lookup CIK for {ticker}: {e}")
            return ""

    def get_filings(
        self,
        ticker: str,
        filing_type: str = "10-K",
        count: int = 5,
    ) -> List[Dict]:
        """
        Get SEC filings for a company.

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            filing_type: Type of filing ("10-K", "10-Q", "8-K", etc.)
            count: Number of filings to return

        Returns:
            List of filing records with keys: accession_number, date, etc.
            Returns empty list on failure.

        Example::

            filings = provider.get_filings("AAPL", "10-K", count=5)
            for filing in filings:
                print(f"{filing['date']}: {filing['accession_number']}")
        """
        if not self.available:
            logger.warning("SEC EDGAR provider not available")
            return []

        try:
            # Get CIK
            cik = self.ticker_to_cik(ticker)
            if not cik:
                logger.warning(f"Could not find CIK for {ticker}")
                return []

            # Get submissions
            url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
            data = self._make_request(url)

            if not data or "filings" not in data:
                logger.warning(f"No filings data for {ticker}")
                return []

            # Filter by filing type
            filings = data["filings"].get("recent", [])
            filtered = []

            for filing in filings:
                if filing.get("form") == filing_type:
                    filtered.append(
                        {
                            "ticker": ticker,
                            "date": filing.get("filingDate"),
                            "accession_number": filing.get("accessionNumber"),
                            "filing_type": filing.get("form"),
                            "size": filing.get("sizeOfCompanyAtFilingInBytes", 0),
                            "is_xbrl": filing.get("isXBRL", 0),
                            "is_inline_xbrl": filing.get("isInlineXBRL", 0),
                        }
                    )

                    if len(filtered) >= count:
                        break

            logger.info(f"Got {len(filtered)} {filing_type} filings for {ticker}")
            return filtered

        except Exception as e:
            logger.error(f"Failed to get filings for {ticker}: {e}")
            return []

    def get_company_facts(self, ticker: str) -> Optional[Dict]:
        """
        Get company facts (standardized financial data from XBRL).

        Args:
            ticker: Stock ticker (e.g., "AAPL")

        Returns:
            Dict with standardized facts organized by taxonomy.
            Returns None on failure.

        Example::

            facts = provider.get_company_facts("AAPL")
            # Returns facts like Assets, Liabilities, etc.
        """
        if not self.available:
            logger.warning("SEC EDGAR provider not available")
            return None

        try:
            # Get CIK
            cik = self.ticker_to_cik(ticker)
            if not cik:
                logger.warning(f"Could not find CIK for {ticker}")
                return None

            # Get facts
            url = f"{self.BASE_URL}/facts/CIK{cik}.json"
            data = self._make_request(url)

            if not data:
                logger.warning(f"No company facts for {ticker}")
                return None

            logger.info(f"Got company facts for {ticker}")
            return data

        except Exception as e:
            logger.error(f"Failed to get company facts for {ticker}: {e}")
            return None

    def get_submissions(self, cik: str) -> Optional[Dict]:
        """
        Get all submissions for a company.

        Args:
            cik: CIK number (can be with or without leading zeros)

        Returns:
            Dict with filings, former names, addresses, etc.
            Returns None on failure.

        Example::

            subs = provider.get_submissions("0000320193")
            # Access: subs["filings"]["recent"] for recent filings
        """
        if not self.available:
            logger.warning("SEC EDGAR provider not available")
            return None

        try:
            # Normalize CIK (remove dashes, pad to 10 digits)
            cik_clean = cik.replace("-", "")
            cik_padded = f"{int(cik_clean):010d}"

            url = f"{self.SUBMISSIONS_URL}/CIK{cik_padded}.json"
            data = self._make_request(url)

            if not data:
                logger.warning(f"No submissions for CIK {cik}")
                return None

            logger.info(f"Got submissions for CIK {cik}")
            return data

        except Exception as e:
            logger.error(f"Failed to get submissions for CIK {cik}: {e}")
            return None

    def search_filings(
        self,
        ticker: str,
        filing_type: Optional[str] = None,
        from_date: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for filings with optional date range.

        Args:
            ticker: Stock ticker
            filing_type: Optional filing type filter
            from_date: Optional from date (YYYY-MM-DD)

        Returns:
            List of matching filings.
        """
        if not self.available:
            logger.warning("SEC EDGAR provider not available")
            return []

        try:
            # Get CIK
            cik = self.ticker_to_cik(ticker)
            if not cik:
                return []

            # Get all submissions
            url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
            data = self._make_request(url)

            if not data:
                return []

            filings = data["filings"].get("recent", [])
            results = []

            for filing in filings:
                # Filter by type if specified
                if filing_type and filing.get("form") != filing_type:
                    continue

                # Filter by date if specified
                filing_date = filing.get("filingDate")
                if from_date and filing_date < from_date:
                    continue

                results.append(
                    {
                        "ticker": ticker,
                        "date": filing_date,
                        "accession_number": filing.get("accessionNumber"),
                        "filing_type": filing.get("form"),
                    }
                )

            logger.info(f"Found {len(results)} filings for {ticker}")
            return results

        except Exception as e:
            logger.error(f"Failed to search filings for {ticker}: {e}")
            return []

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "name": "SEC EDGAR",
            "available": self.available,
            "library_available": REQUESTS_AVAILABLE,
            "api_key_required": False,
            "rate_limit": "10 requests/second",
            "user_agent": self.user_agent,
        }
