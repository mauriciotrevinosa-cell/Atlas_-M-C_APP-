"""
Tick-based runner that orchestrates analysis modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from threading import Event, Lock, Thread
import time
from typing import Iterable

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.analytics.modules.base import AnalysisModule, SimulationTickContext
from atlas.core.engine.event_bus import EventBus

logger = logging.getLogger("atlas.simulation.runner")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationRunner:
    def __init__(
        self,
        event_bus: EventBus,
        modules: Iterable[AnalysisModule],
        *,
        tick_interval_seconds: float = 1.0,
        runner_id: str = "simulation_runner",
    ) -> None:
        self._event_bus = event_bus
        self._modules = {module.module_id: module for module in modules}
        self._active_modules = set(self._modules.keys())
        self._tick_interval_seconds = tick_interval_seconds
        self._runner_id = runner_id
        self._tick = 0
        self._started_at = _utc_now()
        self._inputs: dict[str, object] = {}

        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def tick_count(self) -> int:
        with self._lock:
            return self._tick

    @property
    def tick_interval_seconds(self) -> float:
        return self._tick_interval_seconds

    def set_tick_interval_seconds(self, interval: float) -> None:
        if interval <= 0:
            raise ValueError("tick interval must be > 0")
        self._tick_interval_seconds = interval

    def set_active_modules(self, module_ids: Iterable[str]) -> None:
        candidate = set(module_ids)
        unknown = candidate - set(self._modules.keys())
        if unknown:
            raise ValueError(f"Unknown module ids: {sorted(unknown)}")
        self._active_modules = candidate

    def set_inputs(self, inputs: dict[str, object]) -> None:
        with self._lock:
            self._inputs = dict(inputs)

    def get_inputs(self) -> dict[str, object]:
        with self._lock:
            return dict(self._inputs)

    def module_ids(self) -> list[str]:
        return sorted(self._modules.keys())

    def active_module_ids(self) -> list[str]:
        return sorted(self._active_modules)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._publish_internal_log("Simulation runner started")

    def stop(self, timeout: float = 2.0) -> None:
        if not self.is_running():
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None
        self._publish_internal_log("Simulation runner stopped")

    def run_tick(self) -> None:
        now = _utc_now()
        with self._lock:
            self._tick += 1
            tick = self._tick
            started_at = self._started_at
            inputs = dict(self._inputs)

        context = SimulationTickContext(
            tick=tick,
            started_at=started_at,
            timestamp=now,
            tick_interval_seconds=self._tick_interval_seconds,
            demo_mode=True,
            inputs=inputs,
        )

        for module_id in sorted(self._active_modules):
            module = self._modules[module_id]
            try:
                module.on_tick(context, self._event_bus.publish)
            except Exception as exc:
                logger.exception("Module '%s' failed on tick=%s", module_id, tick)
                self._event_bus.publish(
                    Artifact(
                        artifact_type=ArtifactType.EVENT,
                        title="Module Execution Error",
                        module_id=module_id,
                        payload={
                            "message": f"{module_id} failed on tick={tick}: {exc}",
                            "severity": "error",
                        },
                        tags=["runner", "error"],
                        published_by=self._runner_id,
                        tick=tick,
                    )
                )

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            cycle_start = time.perf_counter()
            self.run_tick()
            elapsed = time.perf_counter() - cycle_start
            wait_seconds = max(0.0, self._tick_interval_seconds - elapsed)
            self._stop_event.wait(wait_seconds)

    def _publish_internal_log(self, message: str) -> None:
        self._event_bus.publish(
            Artifact(
                artifact_type=ArtifactType.LOG,
                title="Runner Log",
                module_id="simulation_runner",
                payload={"message": message},
                tags=["runner", "lifecycle"],
                published_by=self._runner_id,
                tick=self.tick_count,
            )
        )
