"""
Tests for SimulationRunner tick orchestration.
"""

from __future__ import annotations

import time

from atlas.core.analytics.artifacts import ArtifactType
from atlas.core.analytics.modules import (
    CommodityConcentrationMonitorModule,
    MarketStateModule,
)
from atlas.core.engine.artifact_registry import ArtifactRegistry
from atlas.core.engine.event_bus import EventBus
from atlas.core.engine.simulation_runner import SimulationRunner


def test_simulation_runner_single_tick_publishes_from_all_modules() -> None:
    registry = ArtifactRegistry(cache_size=500)
    bus = EventBus(registry=registry)
    runner = SimulationRunner(
        event_bus=bus,
        modules=[MarketStateModule(seed=1), CommodityConcentrationMonitorModule(seed=2)],
        tick_interval_seconds=1.0,
    )

    runner.run_tick()

    assert runner.tick_count == 1

    history = registry.get_history(limit=500)
    module_ids = {artifact.module_id for artifact in history}
    artifact_types = {artifact.artifact_type for artifact in history}

    assert "market_state" in module_ids
    assert "commodity_concentration" in module_ids
    assert ArtifactType.HISTOGRAM in artifact_types
    assert ArtifactType.TABLE in artifact_types
    assert ArtifactType.SCALAR in artifact_types


def test_simulation_runner_background_loop_increments_tick() -> None:
    registry = ArtifactRegistry(cache_size=500)
    bus = EventBus(registry=registry)
    runner = SimulationRunner(
        event_bus=bus,
        modules=[MarketStateModule(seed=1), CommodityConcentrationMonitorModule(seed=2)],
        tick_interval_seconds=0.05,
    )

    runner.start()
    try:
        time.sleep(0.18)
    finally:
        runner.stop()

    assert runner.tick_count >= 2
    assert registry.total_artifacts() > 0

