"""
Tests for artifact schema and payload validation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from atlas.core.analytics.artifacts import Artifact, ArtifactType


def test_valid_histogram_artifact_schema() -> None:
    artifact = Artifact(
        artifact_type=ArtifactType.HISTOGRAM,
        title="Regime Probabilities",
        module_id="market_state",
        payload={
            "bins": ["Trending", "Ranging", "Stressed"],
            "counts": [45.0, 35.0, 20.0],
        },
        tags=["demo", "risk"],
        created_at=datetime.now(timezone.utc),
        published_by="market_state",
        tick=1,
    )

    assert artifact.artifact_type == ArtifactType.HISTOGRAM
    assert artifact.created_at.tzinfo is not None
    assert artifact.module_id == "market_state"


def test_invalid_scalar_artifact_missing_value_fails() -> None:
    with pytest.raises(ValueError):
        Artifact(
            artifact_type=ArtifactType.SCALAR,
            title="Risk",
            module_id="market_state",
            payload={"unit": "score"},
        )


def test_artifact_roundtrip_record_serialization() -> None:
    original = Artifact(
        artifact_type=ArtifactType.EVENT,
        title="Risk Threshold Event",
        module_id="market_state",
        payload={"message": "Risk score high", "severity": "warning"},
        tags=["alert"],
        published_by="market_state",
        tick=10,
        metadata={"source": "test"},
    )
    original.sequence = 42

    recovered = Artifact.from_record(original.to_record())

    assert recovered.sequence == 42
    assert recovered.artifact_type == ArtifactType.EVENT
    assert recovered.payload["severity"] == "warning"
    assert recovered.tags == ["alert"]

