from __future__ import annotations

from atlas.data_layer.sources.prediction import PolymarketGammaProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeGammaSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=15):
        self.calls.append((url, params))
        if url.endswith("/markets/123"):
            return FakeResponse(
                {
                    "id": "123",
                    "conditionId": "0xabc",
                    "question": "Will CPI be above consensus?",
                    "active": True,
                    "closed": False,
                    "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["0.62", "0.38"]',
                    "clobTokenIds": '["token-yes", "token-no"]',
                    "volume": "10000.5",
                }
            )
        if params and params.get("slug") == "cpi-above-consensus":
            return FakeResponse(
                [
                    {
                        "id": "123",
                        "conditionId": "0xabc",
                        "slug": "cpi-above-consensus",
                        "question": "Will CPI be above consensus?",
                        "active": True,
                        "closed": False,
                        "outcomes": ["Yes", "No"],
                        "outcomePrices": ["0.62", "0.38"],
                        "clobTokenIds": ["token-yes", "token-no"],
                    }
                ]
            )
        if params and params.get("condition_ids") == "0xabc":
            return FakeResponse(
                [
                    {
                        "id": "123",
                        "conditionId": "0xabc",
                        "slug": "cpi-above-consensus",
                        "question": "Will CPI be above consensus?",
                        "active": True,
                        "closed": False,
                        "outcomes": ["Yes", "No"],
                        "outcomePrices": ["0.62", "0.38"],
                        "clobTokenIds": ["token-yes", "token-no"],
                    }
                ]
            )
        return FakeResponse(
            [
                {
                    "id": "123",
                    "conditionId": "0xabc",
                    "slug": "cpi-above-consensus",
                    "question": "Will CPI be above consensus?",
                    "active": True,
                    "closed": False,
                    "outcomes": ["Yes", "No"],
                    "outcomePrices": ["0.62", "0.38"],
                    "clobTokenIds": ["token-yes", "token-no"],
                    "liquidity": "2500",
                }
            ]
        )


def test_polymarket_search_markets_is_read_only_and_normalized() -> None:
    session = FakeGammaSession()
    provider = PolymarketGammaProvider(session=session)

    markets = provider.search_markets("CPI", limit=5)

    assert len(markets) == 1
    assert markets[0]["provider"] == "PolymarketGamma"
    assert markets[0]["read_only"] is True
    assert markets[0]["probabilities"] == {"Yes": 0.62, "No": 0.38}
    assert markets[0]["outcome_tokens"][0]["token_id"] == "token-yes"
    assert session.calls[0][1]["q"] == "CPI"


def test_polymarket_get_market_parses_json_encoded_fields() -> None:
    provider = PolymarketGammaProvider(session=FakeGammaSession())

    market = provider.get_market("123")

    assert market is not None
    assert market["condition_id"] == "0xabc"
    assert market["volume"] == 10000.5
    assert market["probabilities"]["Yes"] == 0.62
    assert market["clob_token_ids"] == ["token-yes", "token-no"]


def test_polymarket_find_market_by_slug_selects_outcome() -> None:
    provider = PolymarketGammaProvider(session=FakeGammaSession())

    market = provider.find_market("cpi-above-consensus", outcome="Yes")

    assert market is not None
    assert market["slug"] == "cpi-above-consensus"
    assert market["selected_outcome"] == {
        "outcome": "Yes",
        "token_id": "token-yes",
        "probability": 0.62,
    }


def test_polymarket_resolve_outcome_accepts_token_id() -> None:
    provider = PolymarketGammaProvider(session=FakeGammaSession())

    outcome = provider.resolve_outcome("0xabc", "token-no")

    assert outcome == {
        "outcome": "No",
        "token_id": "token-no",
        "probability": 0.38,
    }


def test_polymarket_provider_info_disables_trading() -> None:
    provider = PolymarketGammaProvider(session=FakeGammaSession())

    info = provider.get_info()

    assert info["mode"] == "read_only"
    assert info["trading_supported"] is False
