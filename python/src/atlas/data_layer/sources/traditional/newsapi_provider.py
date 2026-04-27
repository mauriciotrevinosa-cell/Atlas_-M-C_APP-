"""
NewsAPI Data Provider

Fetches news headlines and articles from NewsAPI.
Uses requests library directly.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from typing import Optional, Dict, List, Any

logger = logging.getLogger("atlas.data_layer.newsapi_provider")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NewsAPIProvider:
    """
    Fetches news articles from NewsAPI.

    Provides headlines and detailed article search.
    Requires NEWSAPI_KEY environment variable.

    Example::

        provider = NewsAPIProvider()
        if provider.available:
            headlines = provider.get_headlines(country='us', category='business')
            articles = provider.get_everything(
                query='Apple',
                from_date='2024-01-01',
                to_date='2024-12-31'
            )
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self):
        """Initialize NewsAPI provider with API key from environment"""
        self.available = False
        self.api_key = os.environ.get("NEWSAPI_KEY")

        if not self.api_key:
            logger.warning("NEWSAPI_KEY not found in environment")
            return

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")
            return

        self.available = True
        logger.info("NewsAPI provider initialized")

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Make authenticated request to NewsAPI.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response or None on failure
        """
        if params is None:
            params = {}

        params["apiKey"] = self.api_key

        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return None

            return data

        except Exception as e:
            logger.error(f"NewsAPI request failed ({endpoint}): {e}")
            return None

    def get_headlines(
        self,
        query: Optional[str] = None,
        country: str = "us",
        category: str = "business",
        sort_by: str = "publishedAt",
        page_size: int = 20,
        page: int = 1,
    ) -> List[Dict]:
        """
        Get top news headlines.

        Args:
            query: Optional search query
            country: Country code (us, gb, ca, etc.)
            category: News category (business, entertainment, health, science, sports, technology)
            sort_by: Sort order (publishedAt, relevancy, popularity)
            page_size: Articles per page (max 100)
            page: Page number for pagination

        Returns:
            List of headline articles.
            Returns empty list on failure.

        Example::

            headlines = provider.get_headlines(country='us', category='technology')
            for article in headlines:
                print(f"{article['title']} - {article['source']['name']}")
        """
        if not self.available:
            logger.warning("NewsAPI provider not available")
            return []

        try:
            params = {
                "pageSize": min(page_size, 100),
                "page": page,
                "sortBy": sort_by,
            }

            if query:
                # Use everything endpoint for query
                params["q"] = query
                endpoint = "everything"
            else:
                # Use top-headlines endpoint
                params["country"] = country
                params["category"] = category
                endpoint = "top-headlines"

            data = self._make_request(endpoint, params)

            if data is None:
                return []

            articles = data.get("articles", [])
            logger.info(
                f"Got {len(articles)} headlines "
                f"(country={country}, category={category})"
            )
            return articles

        except Exception as e:
            logger.error(f"Failed to get headlines: {e}")
            return []

    def get_everything(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 20,
        page: int = 1,
    ) -> List[Dict]:
        """
        Search for articles across all sources.

        Args:
            query: Search query (required)
            from_date: From date (YYYY-MM-DD)
            to_date: To date (YYYY-MM-DD)
            language: Language code (en, es, fr, de, it, pt, ru, ar, he, zh, etc.)
            sort_by: Sort order (relevancy, popularity, publishedAt)
            page_size: Articles per page (max 100)
            page: Page number for pagination

        Returns:
            List of articles.
            Returns empty list on failure.

        Example::

            articles = provider.get_everything(
                query='Apple earnings',
                from_date='2024-01-01',
                to_date='2024-12-31',
                sort_by='relevancy'
            )
        """
        if not self.available:
            logger.warning("NewsAPI provider not available")
            return []

        try:
            params = {
                "q": query,
                "language": language,
                "sortBy": sort_by,
                "pageSize": min(page_size, 100),
                "page": page,
            }

            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            data = self._make_request("everything", params)

            if data is None:
                return []

            articles = data.get("articles", [])
            total_results = data.get("totalResults", 0)

            logger.info(
                f"Got {len(articles)} articles for query '{query}' "
                f"({total_results} total available)"
            )
            return articles

        except Exception as e:
            logger.error(f"Failed to search articles: {e}")
            return []

    def search_by_symbol(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page_size: int = 20,
    ) -> List[Dict]:
        """
        Search for news about a specific stock symbol.

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            from_date: From date (YYYY-MM-DD)
            to_date: To date (YYYY-MM-DD)
            page_size: Articles per page

        Returns:
            List of articles mentioning the symbol.
        """
        if not self.available:
            logger.warning("NewsAPI provider not available")
            return []

        return self.get_everything(
            query=symbol,
            from_date=from_date,
            to_date=to_date,
            sort_by="relevancy",
            page_size=page_size,
        )

    def search_by_company(
        self,
        company_name: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page_size: int = 20,
    ) -> List[Dict]:
        """
        Search for news about a specific company.

        Args:
            company_name: Company name (e.g., "Apple Inc")
            from_date: From date (YYYY-MM-DD)
            to_date: To date (YYYY-MM-DD)
            page_size: Articles per page

        Returns:
            List of articles about the company.
        """
        if not self.available:
            logger.warning("NewsAPI provider not available")
            return []

        return self.get_everything(
            query=company_name,
            from_date=from_date,
            to_date=to_date,
            sort_by="relevancy",
            page_size=page_size,
        )

    def get_trending_topics(
        self,
        language: str = "en",
        page_size: int = 20,
    ) -> List[Dict]:
        """
        Get trending news topics.

        Args:
            language: Language code
            page_size: Articles per page

        Returns:
            List of trending articles.
        """
        if not self.available:
            logger.warning("NewsAPI provider not available")
            return []

        try:
            params = {
                "language": language,
                "pageSize": min(page_size, 100),
                "sortBy": "popularity",
            }

            data = self._make_request("everything", params)

            if data is None:
                return []

            articles = data.get("articles", [])
            logger.info(f"Got {len(articles)} trending articles")
            return articles

        except Exception as e:
            logger.error(f"Failed to get trending topics: {e}")
            return []

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "name": "NewsAPI",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "library_available": REQUESTS_AVAILABLE,
            "features": [
                "Top headlines by country/category",
                "Full article search",
                "Symbol-specific news",
                "Company news search",
            ],
        }
