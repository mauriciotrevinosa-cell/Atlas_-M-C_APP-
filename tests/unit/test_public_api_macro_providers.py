from __future__ import annotations

from atlas.data_layer.provider_registry import DataProviderRegistry
from atlas.data_layer.sources.traditional import (
    BLSProvider,
    IMFDataMapperProvider,
    TreasuryFiscalProvider,
    WorldBankProvider,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeWorldBankSession:
    def get(self, url, params=None, timeout=15):
        assert "api.worldbank.org" in url
        assert params["format"] == "json"
        return FakeResponse(
            [
                {"page": 1},
                [
                    {
                        "date": "2024",
                        "value": 29184800000000,
                        "countryiso3code": "USA",
                    }
                ],
            ]
        )


class FakeBLSSession:
    def post(self, url, json=None, timeout=15):
        assert "api.bls.gov" in url
        assert json["seriesid"] == ["LNS14000000"]
        return FakeResponse(
            {
                "status": "REQUEST_SUCCEEDED",
                "Results": {
                    "series": [
                        {
                            "seriesID": "LNS14000000",
                            "data": [
                                {"year": "2024", "period": "M01", "value": "3.7"},
                                {"year": "2024", "period": "M13", "value": "annual"},
                            ],
                        }
                    ]
                },
            }
        )


class FakeTreasurySession:
    def get(self, url, params=None, timeout=15):
        assert "api.fiscaldata.treasury.gov" in url
        assert "record_date,tot_pub_debt_out_amt" == params["fields"]
        return FakeResponse(
            {
                "data": [
                    {
                        "record_date": "2024-01-02",
                        "tot_pub_debt_out_amt": "34001234567890.12",
                    }
                ]
            }
        )


class FakeIMFSession:
    def get(self, url, params=None, headers=None, timeout=15):
        assert "imf.org/external/datamapper/api/v2" in url
        assert params["periods"] == "2024"
        return FakeResponse(
            {
                "values": {
                    "NGDP_RPCH": {
                        "USA": {
                            "2024": 2.8,
                        }
                    }
                }
            }
        )


def test_world_bank_provider_parses_indicator_payload() -> None:
    provider = WorldBankProvider(session=FakeWorldBankSession())

    frame = provider.get_series("GDP", start="2024-01-01", end="2024-12-31")

    assert not frame.empty
    assert frame.iloc[0]["value"] == 29184800000000
    assert frame.iloc[0]["series_id"] == "NY.GDP.MKTP.CD"
    assert frame.iloc[0]["provider"] == "WorldBank"


def test_bls_provider_parses_monthly_series_payload() -> None:
    provider = BLSProvider(session=FakeBLSSession())

    frame = provider.get_series("UNEMPLOYMENT", start="2024-01-01", end="2024-12-31")

    assert len(frame) == 1
    assert frame.iloc[0]["value"] == 3.7
    assert frame.iloc[0]["series_id"] == "LNS14000000"


def test_treasury_provider_parses_public_debt_payload() -> None:
    provider = TreasuryFiscalProvider(session=FakeTreasurySession())

    frame = provider.get_series("PUBLIC_DEBT", start="2024-01-01", end="2024-01-31")

    assert not frame.empty
    assert frame.iloc[0]["value"] == 34001234567890.12
    assert frame.iloc[0]["provider"] == "TreasuryFiscal"


def test_imf_provider_parses_datamapper_payload() -> None:
    provider = IMFDataMapperProvider(session=FakeIMFSession())

    frame = provider.get_series("GDP_REAL_GROWTH", start="2024-01-01", end="2024-01-01")

    assert not frame.empty
    assert frame.iloc[0]["value"] == 2.8
    assert frame.iloc[0]["series_id"] == "NGDP_RPCH"
    assert frame.iloc[0]["provider"] == "IMFDataMapper"


def test_default_registry_includes_public_api_macro_fallbacks() -> None:
    registry = DataProviderRegistry()
    macro_names = {item["name"] for item in registry.get_provider_info()["macro"]}

    assert {"BLS", "WorldBank", "TreasuryFiscal", "IMFDataMapper"}.issubset(macro_names)
