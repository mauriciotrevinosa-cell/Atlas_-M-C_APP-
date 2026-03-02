"""
Generic renderers that map artifact types to Streamlit visuals.
"""

from __future__ import annotations

from datetime import timezone

import pandas as pd
import streamlit as st

from atlas.core.analytics.artifacts import Artifact, ArtifactType


def _render_timeseries(artifact: Artifact) -> None:
    points = artifact.payload.get("points", [])
    if not points:
        st.info("No points available.")
        return

    frame = pd.DataFrame(points)
    if "x" not in frame.columns or "y" not in frame.columns:
        st.info("Timeseries payload missing x/y columns.")
        return

    frame["x"] = frame["x"].astype(str)
    if "series" in frame.columns and frame["series"].nunique() > 1:
        pivoted = frame.pivot_table(index="x", columns="series", values="y", aggfunc="last")
        st.line_chart(pivoted)
    else:
        frame = frame.set_index("x")
        st.line_chart(frame["y"])


def _render_histogram(artifact: Artifact) -> None:
    bins = artifact.payload.get("bins", [])
    counts = artifact.payload.get("counts", [])
    if not bins or not counts:
        st.info("Histogram payload is empty.")
        return

    frame = pd.DataFrame({"bin": bins, "count": counts}).set_index("bin")
    st.bar_chart(frame["count"])


def _render_table(artifact: Artifact) -> None:
    columns = artifact.payload.get("columns", [])
    rows = artifact.payload.get("rows", [])
    if not columns:
        st.info("Table payload has no columns.")
        return

    if rows and isinstance(rows[0], dict):
        frame = pd.DataFrame(rows)
    else:
        frame = pd.DataFrame(rows, columns=columns)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_scalar(artifact: Artifact) -> None:
    value = artifact.payload.get("value")
    if value is None:
        st.info("Scalar payload has no value.")
        return

    threshold = artifact.payload.get("threshold")
    min_value = artifact.payload.get("min")
    max_value = artifact.payload.get("max")
    unit = artifact.payload.get("unit", "")

    delta = None
    if threshold is not None and isinstance(value, (int, float)):
        delta = round(float(value) - float(threshold), 2)

    st.metric(
        label=artifact.title,
        value=f"{value} {unit}".strip(),
        delta=delta,
    )

    if (
        isinstance(value, (int, float))
        and isinstance(min_value, (int, float))
        and isinstance(max_value, (int, float))
        and max_value > min_value
    ):
        progress = min(
            1.0,
            max(
                0.0,
                (float(value) - float(min_value))
                / (float(max_value) - float(min_value)),
            ),
        )
        st.progress(progress)


def _render_event(artifact: Artifact) -> None:
    message = str(artifact.payload.get("message", ""))
    severity = str(artifact.payload.get("severity", "info")).lower()
    timestamp = artifact.created_at.astimezone(timezone.utc).strftime("%H:%M:%S")
    text = f"[{timestamp}] {message}"

    if severity == "error":
        st.error(text)
    elif severity == "warning":
        st.warning(text)
    else:
        st.info(text)


def _render_log(artifact: Artifact) -> None:
    message = str(artifact.payload.get("message", ""))
    timestamp = artifact.created_at.astimezone(timezone.utc).strftime("%H:%M:%S")
    st.caption(f"[{timestamp}] {message}")
    values = artifact.payload.get("values")
    if values:
        st.json(values)


def render_artifact(artifact: Artifact) -> None:
    st.subheader(f"{artifact.title} [{artifact.artifact_type.value}]")
    if artifact.artifact_type == ArtifactType.TIMESERIES:
        _render_timeseries(artifact)
    elif artifact.artifact_type == ArtifactType.HISTOGRAM:
        _render_histogram(artifact)
    elif artifact.artifact_type == ArtifactType.TABLE:
        _render_table(artifact)
    elif artifact.artifact_type == ArtifactType.SCALAR:
        _render_scalar(artifact)
    elif artifact.artifact_type == ArtifactType.EVENT:
        _render_event(artifact)
    elif artifact.artifact_type == ArtifactType.LOG:
        _render_log(artifact)
