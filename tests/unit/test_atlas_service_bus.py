"""
Tests for the AtlasServiceBus channel and shared state foundation.
"""

from __future__ import annotations

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.engine.artifact_registry import ArtifactRegistry
from atlas.core.engine.atlas_service_bus import AtlasServiceBus, BusChannel


def test_atlas_service_bus_routes_channels_and_state() -> None:
    registry = ArtifactRegistry(cache_size=200)
    bus = AtlasServiceBus(registry=registry)

    channel_events: list[tuple[BusChannel, str, str]] = []
    state_events: list[tuple[str, float, float | None]] = []

    channel_token = bus.subscribe_channel(
        callback=lambda message: channel_events.append(
            (message.channel, message.published_by, message.payload["symbol"])
        ),
        channels={BusChannel.MARKET_DATA, "NEWS"},
    )
    state_token = bus.subscribe_state(
        callback=lambda change: state_events.append(
            (change.key, change.value, change.previous_value)
        ),
        keys={"portfolio_value"},
    )

    message = bus.publish_channel(
        "market_data",
        {"symbol": "SPY", "price": 512.25},
        published_by="market_feed",
    )
    change = bus.set_state(
        "portfolio_value",
        125000.0,
        published_by="risk_engine",
        metadata={"currency": "USD"},
    )
    artifact = bus.publish(
        Artifact(
            artifact_type=ArtifactType.LOG,
            title="Service Bus Log",
            module_id="market_state",
            payload={"message": "channel and state update complete"},
            published_by="market_state",
        )
    )

    assert message.channel is BusChannel.MARKET_DATA
    assert message.sequence == 1
    assert channel_events == [(BusChannel.MARKET_DATA, "market_feed", "SPY")]
    assert bus.latest_channel_message(BusChannel.MARKET_DATA) == message

    assert change.key == "portfolio_value"
    assert change.value == 125000.0
    assert change.previous_value is None
    assert state_events == [("portfolio_value", 125000.0, None)]
    assert bus.get_state("portfolio_value") == 125000.0
    assert bus.get_state_snapshot() == {"portfolio_value": 125000.0}
    assert bus.get_state_history("portfolio_value") == [change]

    assert artifact.sequence == 1
    assert registry.get_latest("market_state") == artifact

    assert bus.unsubscribe_channel(channel_token) is True
    assert bus.unsubscribe_state(state_token) is True
    assert bus.channel_subscriber_count() == 0
    assert bus.state_observer_count() == 0


def test_atlas_service_bus_channel_and_state_history_filtering() -> None:
    bus = AtlasServiceBus()

    bus.publish_channel(BusChannel.NEWS, {"headline": "Fed minutes released"}, published_by="news_feed")
    bus.publish_channel(BusChannel.RISK, {"message": "risk overlay updated"}, published_by="risk_engine")
    bus.set_state("risk_limit", 0.35, published_by="risk_engine")
    bus.set_state("position_limit", 0.20, published_by="risk_engine")

    news_history = bus.get_channel_history("news")
    all_history = bus.get_channel_history(limit=2)
    state_history = bus.get_state_history(limit=1)

    assert len(news_history) == 1
    assert news_history[0].channel is BusChannel.NEWS
    assert len(all_history) == 2
    assert all_history[-1].channel is BusChannel.RISK
    assert len(state_history) == 1
    assert state_history[0].key == "position_limit"
    assert bus.get_state_history("risk_limit")[0].value == 0.35
