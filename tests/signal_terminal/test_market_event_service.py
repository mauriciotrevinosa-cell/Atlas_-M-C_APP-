"""Tests for Signal Terminal market microstructure event ingestion."""

from datetime import datetime, timezone

from atlas.signal_terminal.models import SignalCategory, Urgency
from atlas.signal_terminal.services.alert_service import AlertService
from atlas.signal_terminal.services.market_event_service import MarketEventService
from atlas.signal_terminal.services.signal_service import SignalService
from atlas.signal_terminal.services.whale_service import WhaleService
from atlas.signal_terminal.storage.repository import SignalRepository


def _service(tmp_path):
    repo = SignalRepository(tmp_path / "signals.db")
    signal_svc = SignalService(repo, AlertService(repo), WhaleService(repo))
    return repo, MarketEventService(signal_svc)


def test_market_event_service_builds_raw_items_for_threshold_crosses(tmp_path):
    _, svc = _service(tmp_path)
    raw_items = svc.build_raw_items([
        {
            "symbol": "BTC",
            "exchange": "hyperliquid",
            "timeframe": "15m",
            "observed_at": "2026-05-12T12:00:00Z",
            "funding_rate": 0.041,
            "open_interest_change_pct": 18,
            "liquidation_usd": 12_500_000,
            "volume_ratio": 2.6,
        }
    ])

    assert len(raw_items) == 4
    assert all(item.source_id == "market_microstructure" for item in raw_items)
    assert all("$BTC" in item.title or "$BTC" in item.body for item in raw_items)
    assert {item.extra["event_type"] for item in raw_items} == {
        "funding_extreme",
        "open_interest_shift",
        "liquidation_spike",
        "volume_spike",
    }


def test_market_event_service_ingests_signals_and_liquidation_whale_event(tmp_path):
    repo, svc = _service(tmp_path)
    observed_at = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)

    result = svc.ingest_snapshots([
        {
            "symbol": "ETH",
            "exchange": "binance",
            "timeframe": "5m",
            "observed_at": observed_at,
            "funding_rate": -0.035,
            "open_interest_change_pct": -15,
            "liquidation_usd": 25_000_000,
            "volume_ratio": 3.0,
        }
    ])

    assert result == {"raw_items": 4, "inserted": 4, "duplicates": 0}

    signals = repo.get_signals(ticker="ETH", limit=10)
    assert len(signals) == 4
    assert all("ETH" in signal.tickers for signal in signals)
    assert {signal.category for signal in signals} <= {
        SignalCategory.CRYPTO,
        SignalCategory.WHALE,
        SignalCategory.TECHNICAL,
    }
    assert any(signal.urgency in {Urgency.MEDIUM, Urgency.HIGH, Urgency.CRITICAL} for signal in signals)

    whales = repo.get_whale_events(ticker="ETH", limit=10)
    assert whales
    assert any(event.event_type == "liquidation" for event in whales)
    assert any(event.size == 25_000_000 for event in whales)


def test_market_event_service_dedupes_same_snapshot(tmp_path):
    _, svc = _service(tmp_path)
    snapshot = {
        "symbol": "SOL",
        "observed_at": "2026-05-12T12:00:00Z",
        "liquidation_usd": 8_000_000,
    }

    first = svc.ingest_snapshots([snapshot])
    second = svc.ingest_snapshots([snapshot])

    assert first == {"raw_items": 1, "inserted": 1, "duplicates": 0}
    assert second == {"raw_items": 1, "inserted": 0, "duplicates": 1}


def test_market_events_endpoint_ingests_snapshot(tmp_path, monkeypatch):
    import importlib

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    router_module = importlib.import_module("atlas.signal_terminal.api.router")

    repo = SignalRepository(tmp_path / "endpoint.db")
    signal_svc = SignalService(repo, AlertService(repo), WhaleService(repo))

    class Scheduler:
        pass

    scheduler = Scheduler()
    scheduler.signal_svc = signal_svc
    scheduler.watch_svc = None
    monkeypatch.setattr(router_module, "get_scheduler", lambda: scheduler)

    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/signals")
    client = TestClient(app)

    response = client.post(
        "/api/signals/market-events",
        json=[
            {
                "symbol": "BTC",
                "observed_at": "2026-05-12T12:00:00Z",
                "liquidation_usd": 9_000_000,
            }
        ],
    )

    assert response.status_code == 200
    assert response.json() == {"raw_items": 1, "inserted": 1, "duplicates": 0}
    assert repo.get_signals(ticker="BTC")


def test_named_signal_routes_are_not_captured_as_signal_ids(tmp_path, monkeypatch):
    import importlib

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    router_module = importlib.import_module("atlas.signal_terminal.api.router")
    repo = SignalRepository(tmp_path / "route-order.db")
    signal_svc = SignalService(repo, AlertService(repo), WhaleService(repo))

    class WatchService:
        def get_sources(self, enabled_only=True):
            return []

        def get_all(self):
            return []

    class Scheduler:
        pass

    scheduler = Scheduler()
    scheduler.signal_svc = signal_svc
    scheduler.watch_svc = WatchService()
    monkeypatch.setattr(router_module, "get_scheduler", lambda: scheduler)

    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/signals")
    client = TestClient(app)

    assert client.get("/api/signals/whales").status_code == 200
    assert client.get("/api/signals/watchlist").status_code == 200
    assert client.get("/api/signals/sources/list").status_code == 200
    missing = client.get("/api/signals/not-a-real-id")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Signal not found"
