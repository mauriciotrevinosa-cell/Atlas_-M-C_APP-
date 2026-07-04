from __future__ import annotations

from datetime import datetime

from apps.server import server


class FakeRegistry:
    def get_provider_info(self):
        return {
            "market_data": [
                {"name": "YahooFinance", "available": True, "priority": 10},
                {"name": "Polygon", "available": False, "priority": 100},
            ],
            "filings": [
                {"name": "SECEDGAR", "available": True, "priority": 100},
            ],
        }

    def get_request_log(self, limit: int = 100):
        return [
            {
                "timestamp": datetime(2026, 5, 11, 12, 0, 0),
                "provider": "YahooFinance",
                "description": "quote for AAPL",
                "success": True,
                "error": None,
            }
        ][:limit]


def test_provider_health_snapshot_summarizes_channels(monkeypatch) -> None:
    monkeypatch.setattr(server, "get_provider_registry", lambda: FakeRegistry())

    payload = server._build_provider_health_snapshot(limit=10)

    assert payload["status"] == "degraded"
    assert payload["channels_total"] == 2
    assert payload["providers_total"] == 3
    assert payload["providers_available"] == 2
    assert payload["providers_unavailable"] == 1
    assert payload["recent_requests"][0]["timestamp"] == "2026-05-11T12:00:00"

    by_channel = {channel["name"]: channel for channel in payload["channels"]}
    assert by_channel["market_data"]["status"] == "online"
    assert by_channel["market_data"]["providers_available"] == 1


def test_provider_health_snapshot_handles_registry_failure(monkeypatch) -> None:
    def fail_registry():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(server, "get_provider_registry", fail_registry)

    payload = server._build_provider_health_snapshot()

    assert payload["status"] == "critical"
    assert payload["providers_total"] == 0
    assert "registry unavailable" in payload["error"]
