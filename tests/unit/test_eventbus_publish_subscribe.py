"""
Tests for publish/subscribe mechanics across EventBus + ArtifactRegistry.
"""

from __future__ import annotations

from atlas.core.analytics.artifacts import Artifact, ArtifactFilter, ArtifactType
from atlas.core.engine.artifact_registry import ArtifactRegistry
from atlas.core.engine.event_bus import EventBus


def test_eventbus_publish_and_filtered_subscription() -> None:
    registry = ArtifactRegistry(cache_size=200)
    bus = EventBus(registry=registry)
    received: list[Artifact] = []

    token = bus.subscribe(
        callback=lambda artifact: received.append(artifact),
        filters=ArtifactFilter(module_ids={"market_state"}),
    )

    bus.publish(
        Artifact(
            artifact_type=ArtifactType.LOG,
            title="Market Log",
            module_id="market_state",
            payload={"message": "market update"},
            published_by="market_state",
        )
    )
    bus.publish(
        Artifact(
            artifact_type=ArtifactType.LOG,
            title="Commodity Log",
            module_id="commodity_concentration",
            payload={"message": "commodity update"},
            published_by="commodity_concentration",
        )
    )

    assert len(received) == 1
    assert received[0].module_id == "market_state"

    latest_market = registry.get_latest("market_state")
    latest_commodity = registry.get_latest("commodity_concentration")
    assert latest_market is not None
    assert latest_commodity is not None
    assert latest_market.title == "Market Log"
    assert latest_commodity.title == "Commodity Log"

    assert bus.unsubscribe(token) is True
    assert bus.subscriber_count() == 0


def test_registry_history_by_type_and_module() -> None:
    registry = ArtifactRegistry(cache_size=200)
    bus = EventBus(registry=registry)

    bus.publish(
        Artifact(
            artifact_type=ArtifactType.SCALAR,
            title="Risk Score",
            module_id="market_state",
            payload={"value": 55.0},
            published_by="market_state",
        )
    )
    bus.publish(
        Artifact(
            artifact_type=ArtifactType.EVENT,
            title="Risk Event",
            module_id="market_state",
            payload={"message": "warning", "severity": "warning"},
            published_by="market_state",
        )
    )

    scalar_history = registry.get_history(
        module_id="market_state",
        artifact_type=ArtifactType.SCALAR,
    )
    event_history = registry.get_history(
        module_id="market_state",
        artifact_type=ArtifactType.EVENT,
    )

    assert len(scalar_history) == 1
    assert len(event_history) == 1
    assert scalar_history[0].title == "Risk Score"
    assert event_history[0].title == "Risk Event"

