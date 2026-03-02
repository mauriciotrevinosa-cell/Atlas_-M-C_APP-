"""
Typed artifact schema used by analysis modules and UI renderers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import uuid


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class ArtifactType(str, Enum):
    TIMESERIES = "TIMESERIES"
    HISTOGRAM = "HISTOGRAM"
    TABLE = "TABLE"
    SCALAR = "SCALAR"
    EVENT = "EVENT"
    LOG = "LOG"


def coerce_artifact_type(value: ArtifactType | str) -> ArtifactType:
    if isinstance(value, ArtifactType):
        return value
    return ArtifactType(str(value).upper())


def _validate_timeseries_payload(payload: Mapping[str, Any]) -> None:
    points = payload.get("points")
    if not isinstance(points, list) or not points:
        raise ValueError("TIMESERIES payload requires non-empty 'points' list")
    for point in points:
        if not isinstance(point, Mapping):
            raise ValueError("TIMESERIES points must be mappings")
        if "x" not in point or "y" not in point:
            raise ValueError("Each TIMESERIES point requires 'x' and 'y'")
        if not _is_number(point["y"]):
            raise ValueError("TIMESERIES point 'y' must be numeric")


def _validate_histogram_payload(payload: Mapping[str, Any]) -> None:
    bins = payload.get("bins")
    counts = payload.get("counts")
    if not isinstance(bins, list) or not isinstance(counts, list):
        raise ValueError("HISTOGRAM payload requires 'bins' and 'counts' lists")
    if not bins or len(bins) != len(counts):
        raise ValueError("HISTOGRAM bins/counts must be non-empty and same length")
    if not all(_is_number(value) for value in counts):
        raise ValueError("HISTOGRAM counts must be numeric")


def _validate_table_payload(payload: Mapping[str, Any]) -> None:
    columns = payload.get("columns")
    rows = payload.get("rows")
    if not isinstance(columns, list) or not columns:
        raise ValueError("TABLE payload requires non-empty 'columns' list")
    if not isinstance(rows, list):
        raise ValueError("TABLE payload requires 'rows' list")
    for row in rows:
        if not isinstance(row, (list, tuple, Mapping)):
            raise ValueError("TABLE rows must be list/tuple/mapping values")


def _validate_scalar_payload(payload: Mapping[str, Any]) -> None:
    if "value" not in payload:
        raise ValueError("SCALAR payload requires 'value'")
    if not _is_number(payload["value"]):
        raise ValueError("SCALAR payload 'value' must be numeric")
    for key in ("min", "max", "threshold"):
        value = payload.get(key)
        if value is not None and not _is_number(value):
            raise ValueError(f"SCALAR payload '{key}' must be numeric if provided")


def _validate_event_payload(payload: Mapping[str, Any]) -> None:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("EVENT payload requires non-empty 'message'")
    severity = payload.get("severity")
    if severity is not None and str(severity).lower() not in {"info", "warning", "error"}:
        raise ValueError("EVENT severity must be one of: info, warning, error")


def _validate_log_payload(payload: Mapping[str, Any]) -> None:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("LOG payload requires non-empty 'message'")


def validate_payload(artifact_type: ArtifactType, payload: Mapping[str, Any]) -> None:
    validators = {
        ArtifactType.TIMESERIES: _validate_timeseries_payload,
        ArtifactType.HISTOGRAM: _validate_histogram_payload,
        ArtifactType.TABLE: _validate_table_payload,
        ArtifactType.SCALAR: _validate_scalar_payload,
        ArtifactType.EVENT: _validate_event_payload,
        ArtifactType.LOG: _validate_log_payload,
    }
    validators[artifact_type](payload)


@dataclass
class Artifact:
    artifact_type: ArtifactType | str
    title: str
    module_id: str
    payload: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    published_by: str = "simulation_runner"
    tick: int | None = None
    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sequence: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.artifact_type = coerce_artifact_type(self.artifact_type)
        self.title = str(self.title).strip()
        self.module_id = str(self.module_id).strip()

        if not self.title:
            raise ValueError("Artifact title cannot be empty")
        if not self.module_id:
            raise ValueError("Artifact module_id cannot be empty")
        if not isinstance(self.payload, dict):
            raise ValueError("Artifact payload must be a dict")

        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        else:
            self.created_at = self.created_at.astimezone(timezone.utc)

        unique_tags: list[str] = []
        for raw_tag in self.tags:
            tag = str(raw_tag).strip()
            if tag and tag not in unique_tags:
                unique_tags.append(tag)
        self.tags = unique_tags

        if self.tick is not None and self.tick < 0:
            raise ValueError("Artifact tick must be >= 0")

        validate_payload(self.artifact_type, self.payload)

    def to_record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "sequence": self.sequence,
            "artifact_type": self.artifact_type.value,
            "title": self.title,
            "module_id": self.module_id,
            "payload": self.payload,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "published_by": self.published_by,
            "tick": self.tick,
            "metadata": self.metadata,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Artifact":
        created_at_raw = record.get("created_at")
        if isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.fromisoformat(str(created_at_raw))

        return cls(
            artifact_id=str(record.get("artifact_id", uuid.uuid4().hex)),
            sequence=record.get("sequence"),
            artifact_type=coerce_artifact_type(record["artifact_type"]),
            title=str(record["title"]),
            module_id=str(record["module_id"]),
            payload=dict(record["payload"]),
            tags=list(record.get("tags", [])),
            created_at=created_at,
            published_by=str(record.get("published_by", "unknown")),
            tick=record.get("tick"),
            metadata=dict(record.get("metadata", {})),
        )


@dataclass
class ArtifactFilter:
    module_ids: set[str] | None = None
    artifact_types: set[ArtifactType] | None = None
    tags: set[str] | None = None

    def __post_init__(self) -> None:
        if self.module_ids is not None:
            self.module_ids = {str(module_id).strip() for module_id in self.module_ids if module_id}
        if self.artifact_types is not None:
            self.artifact_types = {
                coerce_artifact_type(artifact_type) for artifact_type in self.artifact_types
            }
        if self.tags is not None:
            self.tags = {str(tag).strip() for tag in self.tags if tag}

    def matches(self, artifact: Artifact) -> bool:
        if self.module_ids and artifact.module_id not in self.module_ids:
            return False
        if self.artifact_types and artifact.artifact_type not in self.artifact_types:
            return False
        if self.tags and not self.tags.intersection(set(artifact.tags)):
            return False
        return True


@dataclass(frozen=True)
class AuditRecord:
    sequence: int
    artifact_id: str
    module_id: str
    artifact_type: ArtifactType
    title: str
    published_by: str
    created_at: datetime

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "AuditRecord":
        sequence = artifact.sequence if artifact.sequence is not None else -1
        return cls(
            sequence=sequence,
            artifact_id=artifact.artifact_id,
            module_id=artifact.module_id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            published_by=artifact.published_by,
            created_at=artifact.created_at,
        )

