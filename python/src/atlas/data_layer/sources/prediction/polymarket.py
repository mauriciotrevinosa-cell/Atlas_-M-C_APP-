"""
Polymarket Gamma API read-only provider.

Atlas-owned adapter rebuilt from public documentation and the Folder 4
prediction-market intake item. This provider intentionally exposes market data
only. It does not place, cancel, sign, or manage orders.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.data_layer.polymarket")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


class PolymarketGammaProvider:
    """Read-only client for Polymarket Gamma markets/events data."""

    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, session: Optional[Any] = None):
        self.available = REQUESTS_AVAILABLE
        self.session = session or (requests.Session() if requests else None)

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")

    def search_markets(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        active: bool = True,
        closed: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search/read markets and return Atlas-normalized records."""
        if not self.available or self.session is None:
            return []

        params: Dict[str, Any] = {
            "limit": max(1, min(int(limit), 100)),
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if query:
            params["q"] = query

        payload = self._get("/markets", params=params)
        if not isinstance(payload, list):
            return []
        return [self._normalize_market(item) for item in payload if isinstance(item, dict)]

    def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch one market by Gamma market id."""
        if not market_id:
            return None
        payload = self._get(f"/markets/{market_id}", params={})
        if not isinstance(payload, dict):
            return None
        return self._normalize_market(payload)

    def find_market(
        self,
        identifier: str,
        *,
        outcome: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a market by id, condition id, slug, or search text.

        Returns the normalized market plus `selected_outcome` when an outcome
        name/token is provided. Read-only: no order or wallet operations.
        """
        if not identifier:
            return None

        ident = str(identifier).strip()

        # Numeric Gamma market id.
        if ident.isdigit():
            market = self.get_market(ident)
            return self._with_selected_outcome(market, outcome)

        # Condition id lookup through the markets collection.
        condition_match = self._first_market({"condition_ids": ident, "limit": 1})
        if condition_match:
            return self._with_selected_outcome(condition_match, outcome)

        # Slug lookup through Gamma. If API ignores slug, exact local fallback below.
        slug_match = self._first_market({"slug": ident, "limit": 1})
        if slug_match and str(slug_match.get("slug") or "").lower() == ident.lower():
            return self._with_selected_outcome(slug_match, outcome)

        # Search fallback, favor exact slug/question before first result.
        candidates = self.search_markets(query=ident, limit=10)
        if not candidates:
            return None
        lowered = ident.lower()
        for candidate in candidates:
            if str(candidate.get("slug") or "").lower() == lowered:
                return self._with_selected_outcome(candidate, outcome)
            if str(candidate.get("condition_id") or "").lower() == lowered:
                return self._with_selected_outcome(candidate, outcome)
            if str(candidate.get("question") or "").lower() == lowered:
                return self._with_selected_outcome(candidate, outcome)
        return self._with_selected_outcome(candidates[0], outcome)

    def resolve_outcome(
        self,
        identifier: str,
        outcome: str,
    ) -> Optional[Dict[str, Any]]:
        """Resolve one outcome token/probability inside a market."""
        market = self.find_market(identifier, outcome=outcome)
        if not market:
            return None
        return market.get("selected_outcome")

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "PolymarketGamma",
            "available": self.available,
            "api_key_required": False,
            "mode": "read_only",
            "trading_supported": False,
        }

    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self.BASE_URL}{path}"
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("Polymarket Gamma request failed for %s: %s", path, exc)
            return None

    def _first_market(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.available or self.session is None:
            return None
        payload = self._get("/markets", params=params)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return self._normalize_market(payload[0])
        if isinstance(payload, dict):
            return self._normalize_market(payload)
        return None

    def _normalize_market(self, item: Dict[str, Any]) -> Dict[str, Any]:
        outcomes = self._parse_sequence(item.get("outcomes"))
        prices = self._parse_sequence(item.get("outcomePrices"))
        token_ids = self._parse_sequence(item.get("clobTokenIds") or item.get("tokens"))
        probabilities = self._pair_probabilities(outcomes, prices)
        outcome_tokens = self._pair_outcome_tokens(outcomes, prices, token_ids)

        return {
            "provider": "PolymarketGamma",
            "market_id": str(item.get("id") or item.get("conditionId") or ""),
            "condition_id": item.get("conditionId"),
            "question": item.get("question") or item.get("title") or "",
            "slug": item.get("slug"),
            "active": bool(item.get("active")),
            "closed": bool(item.get("closed")),
            "volume": self._to_float(item.get("volume")),
            "liquidity": self._to_float(item.get("liquidity")),
            "end_date": item.get("endDate") or item.get("endDateIso"),
            "outcomes": outcomes,
            "clob_token_ids": [str(token) for token in token_ids],
            "outcome_tokens": outcome_tokens,
            "probabilities": probabilities,
            "read_only": True,
        }

    def _with_selected_outcome(
        self,
        market: Optional[Dict[str, Any]],
        outcome: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not market or not outcome:
            return market
        selected = self._select_outcome(market, outcome)
        market = dict(market)
        market["selected_outcome"] = selected
        return market

    @staticmethod
    def _select_outcome(market: Dict[str, Any], outcome: str) -> Optional[Dict[str, Any]]:
        target = str(outcome).strip().lower()
        for item in market.get("outcome_tokens", []):
            name = str(item.get("outcome") or "").strip().lower()
            token_id = str(item.get("token_id") or "").strip().lower()
            if target in {name, token_id}:
                return dict(item)
        return None

    @staticmethod
    def _parse_sequence(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return [part.strip() for part in value.split(",") if part.strip()]
        return []

    @staticmethod
    def _pair_probabilities(outcomes: List[Any], prices: List[Any]) -> Dict[str, float]:
        probabilities: Dict[str, float] = {}
        for outcome, price in zip(outcomes, prices):
            try:
                probabilities[str(outcome)] = float(price)
            except (TypeError, ValueError):
                continue
        return probabilities

    @staticmethod
    def _pair_outcome_tokens(
        outcomes: List[Any],
        prices: List[Any],
        token_ids: List[Any],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        max_len = max(len(outcomes), len(prices), len(token_ids))
        for idx in range(max_len):
            outcome = outcomes[idx] if idx < len(outcomes) else None
            price = prices[idx] if idx < len(prices) else None
            token_id = token_ids[idx] if idx < len(token_ids) else None
            rows.append({
                "outcome": str(outcome) if outcome is not None else "",
                "token_id": str(token_id) if token_id is not None else None,
                "probability": PolymarketGammaProvider._to_float(price),
            })
        return rows

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None
