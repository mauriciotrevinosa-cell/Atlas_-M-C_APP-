"""
Streamlit dashboard for the Analysis -> Simulation -> Visualization pipeline.
"""

from __future__ import annotations

from datetime import timezone
import os
from pathlib import Path
import time

import pandas as pd
import streamlit as st

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.analytics.modules import (
    CommodityConcentrationMonitorModule,
    MarketStateModule,
)
from atlas.core.engine import ArtifactRegistry, EventBus, SimulationRunner
from atlas.services.storage import SQLiteArtifactStore
from atlas.ui.artifact_renderers import render_artifact


st.set_page_config(
    page_title="Atlas Simulation Dashboard",
    layout="wide",
)


def _build_runtime() -> dict[str, object]:
    db_path = Path(os.getenv("ATLAS_SIM_ARTIFACT_DB", "data/simulation_artifacts.db"))
    store = SQLiteArtifactStore(db_path=db_path)
    registry = ArtifactRegistry(cache_size=6000, store=store)
    bus = EventBus(registry=registry)

    modules = [
        MarketStateModule(seed=7),
        CommodityConcentrationMonitorModule(seed=13),
    ]
    runner = SimulationRunner(
        event_bus=bus,
        modules=modules,
        tick_interval_seconds=1.0,
        runner_id="simulation_dashboard",
    )

    return {
        "store": store,
        "registry": registry,
        "bus": bus,
        "modules": modules,
        "runner": runner,
    }


def _ensure_session_state() -> dict[str, object]:
    if "simulation_runtime" not in st.session_state:
        runtime = _build_runtime()
        st.session_state["simulation_runtime"] = runtime
        st.session_state["module_artifact_cache"] = {
            module.module_id: {"last_sequence": 0, "artifacts": []}
            for module in runtime["modules"]
        }
        st.session_state["module_visibility"] = {
            module.module_id: True for module in runtime["modules"]
        }
        st.session_state["auto_refresh"] = True
        st.session_state["refresh_seconds"] = 2
    return st.session_state["simulation_runtime"]


def _update_module_cache(runtime: dict[str, object]) -> None:
    registry: ArtifactRegistry = runtime["registry"]
    cache: dict[str, dict[str, object]] = st.session_state["module_artifact_cache"]

    for module_id, module_cache in cache.items():
        last_sequence = int(module_cache["last_sequence"])
        new_artifacts = registry.get_history(
            module_id=module_id,
            since_sequence=last_sequence,
        )
        if not new_artifacts:
            continue

        module_cache["artifacts"].extend(new_artifacts)
        module_cache["artifacts"] = module_cache["artifacts"][-240:]
        module_cache["last_sequence"] = new_artifacts[-1].sequence or last_sequence


def _render_global_timeline(runtime: dict[str, object]) -> None:
    registry: ArtifactRegistry = runtime["registry"]
    history = registry.get_history(limit=500)
    if not history:
        st.info("No artifacts published yet.")
        return

    timeline_rows = [
        {
            "sequence": artifact.sequence,
            "module_id": artifact.module_id,
            "artifact_type": artifact.artifact_type.value,
            "created_at": artifact.created_at.astimezone(timezone.utc),
        }
        for artifact in history
    ]
    frame = pd.DataFrame(timeline_rows)
    cumulative = (
        frame.groupby(["sequence", "module_id"])
        .size()
        .unstack(fill_value=0)
        .cumsum()
    )
    st.line_chart(cumulative)


def _render_module_panels(runtime: dict[str, object]) -> None:
    modules = runtime["modules"]
    cache: dict[str, dict[str, object]] = st.session_state["module_artifact_cache"]
    visibility: dict[str, bool] = st.session_state["module_visibility"]

    for module in modules:
        module_id = module.module_id
        if not visibility.get(module_id, True):
            continue

        artifacts: list[Artifact] = cache[module_id]["artifacts"]
        if not artifacts:
            st.subheader(module.title)
            st.info("No artifacts yet for this module.")
            continue

        st.markdown(f"## {module.title}")

        latest_by_type: dict[ArtifactType, Artifact] = {}
        event_log_buffer: list[Artifact] = []
        for artifact in artifacts:
            if artifact.artifact_type in {ArtifactType.EVENT, ArtifactType.LOG}:
                event_log_buffer.append(artifact)
            else:
                latest_by_type[artifact.artifact_type] = artifact

        for artifact_type in [
            ArtifactType.SCALAR,
            ArtifactType.TIMESERIES,
            ArtifactType.HISTOGRAM,
            ArtifactType.TABLE,
        ]:
            artifact = latest_by_type.get(artifact_type)
            if artifact:
                render_artifact(artifact)

        recent_events = [a for a in event_log_buffer if a.artifact_type == ArtifactType.EVENT][-3:]
        recent_logs = [a for a in event_log_buffer if a.artifact_type == ArtifactType.LOG][-3:]
        for artifact in recent_events + recent_logs:
            render_artifact(artifact)

        st.divider()


def _render_audit_trail(runtime: dict[str, object]) -> None:
    registry: ArtifactRegistry = runtime["registry"]
    audit_rows = [
        {
            "sequence": row.sequence,
            "timestamp_utc": row.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "module_id": row.module_id,
            "artifact_type": row.artifact_type.value,
            "title": row.title,
            "published_by": row.published_by,
        }
        for row in registry.get_audit_trail(limit=50)
    ]
    if not audit_rows:
        st.info("Audit trail is empty.")
        return
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)


def _render_recent_errors(runtime: dict[str, object]) -> None:
    registry: ArtifactRegistry = runtime["registry"]
    error_rows = [
        {
            "sequence": artifact.sequence,
            "timestamp_utc": artifact.created_at.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "module_id": artifact.module_id,
            "severity": artifact.payload.get("severity", "info"),
            "message": artifact.payload.get("message", ""),
        }
        for artifact in registry.get_error_events(limit=20)
    ]
    if not error_rows:
        st.success("No warning/error events.")
        return
    st.dataframe(pd.DataFrame(error_rows), use_container_width=True, hide_index=True)


def main() -> None:
    runtime = _ensure_session_state()
    runner: SimulationRunner = runtime["runner"]
    registry: ArtifactRegistry = runtime["registry"]
    modules = runtime["modules"]

    st.title("Atlas Simulation Dashboard")
    st.caption(
        "Analysis modules keep publishing artifacts even when module panels are closed."
    )

    with st.sidebar:
        st.header("Simulation Controls")

        if runner.is_running():
            if st.button("Stop Runner", type="secondary", use_container_width=True):
                runner.stop()
        else:
            if st.button("Start Runner", type="primary", use_container_width=True):
                runner.start()

        interval = st.slider(
            "Tick Interval (seconds)",
            min_value=1,
            max_value=10,
            value=int(runner.tick_interval_seconds),
        )
        runner.set_tick_interval_seconds(float(interval))

        st.markdown("### Module Visibility")
        st.caption("Closing a panel only hides rendering. Modules remain active.")
        visibility: dict[str, bool] = st.session_state["module_visibility"]
        for module in modules:
            visibility[module.module_id] = st.toggle(
                module.title,
                value=visibility.get(module.module_id, True),
                key=f"visibility_{module.module_id}",
            )

        st.markdown("### Refresh")
        st.session_state["auto_refresh"] = st.toggle(
            "Auto Refresh",
            value=st.session_state.get("auto_refresh", True),
        )
        st.session_state["refresh_seconds"] = st.slider(
            "Refresh every (seconds)",
            min_value=1,
            max_value=10,
            value=int(st.session_state.get("refresh_seconds", 2)),
        )

    _update_module_cache(runtime)

    last_update = registry.get_last_update()
    last_update_text = (
        "n/a"
        if not last_update
        else last_update.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    errors_count = len(registry.get_error_events(limit=100))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Runner State", "RUNNING" if runner.is_running() else "STOPPED")
    m2.metric("Tick", runner.tick_count)
    m3.metric("Artifacts Cached", registry.total_artifacts())
    m4.metric("Warning/Error Events", errors_count)
    st.caption(f"Last Update: {last_update_text}")

    st.markdown("## Recent Errors")
    _render_recent_errors(runtime)

    st.markdown("## Global Timeline")
    _render_global_timeline(runtime)

    st.markdown("## Audit Trail")
    _render_audit_trail(runtime)

    st.markdown("## Module Panels")
    _render_module_panels(runtime)

    if st.session_state.get("auto_refresh", True) and runner.is_running():
        time.sleep(int(st.session_state.get("refresh_seconds", 2)))
        st.rerun()


if __name__ == "__main__":
    main()
