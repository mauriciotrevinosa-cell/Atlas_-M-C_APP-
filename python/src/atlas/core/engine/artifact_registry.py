"""
Central in-memory registry for published artifacts.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import logging
from threading import RLock

from atlas.core.analytics.artifacts import Artifact, ArtifactFilter, ArtifactType, AuditRecord
from atlas.services.storage.artifact_store import ArtifactStore

logger = logging.getLogger("atlas.simulation.artifact_registry")


class ArtifactRegistry:
    def __init__(self, cache_size: int = 5000, store: ArtifactStore | None = None) -> None:
        self._lock = RLock()
        self._history: deque[Artifact] = deque(maxlen=cache_size)
        self._audit_trail: deque[AuditRecord] = deque(maxlen=cache_size)
        self._latest_by_module: dict[str, Artifact] = {}
        self._latest_by_module_type: dict[tuple[str, ArtifactType], Artifact] = {}
        self._sequence = 0
        self._store = store

        if self._store:
            for artifact in self._store.load_recent(limit=cache_size):
                self._append_to_cache(artifact)
                if artifact.sequence is not None:
                    self._sequence = max(self._sequence, artifact.sequence)

    def publish(self, artifact: Artifact) -> Artifact:
        with self._lock:
            self._sequence += 1
            artifact.sequence = self._sequence
            self._append_to_cache(artifact)

            if self._store:
                self._store.save(artifact)

        logger.info(
            "artifact_published sequence=%s module=%s type=%s title=%s by=%s",
            artifact.sequence,
            artifact.module_id,
            artifact.artifact_type.value,
            artifact.title,
            artifact.published_by,
        )
        return artifact

    def _append_to_cache(self, artifact: Artifact) -> None:
        self._history.append(artifact)
        self._audit_trail.append(AuditRecord.from_artifact(artifact))
        self._latest_by_module[artifact.module_id] = artifact
        self._latest_by_module_type[(artifact.module_id, artifact.artifact_type)] = artifact

    def get_latest(
        self, module_id: str, artifact_type: ArtifactType | None = None
    ) -> Artifact | None:
        with self._lock:
            if artifact_type is None:
                return self._latest_by_module.get(module_id)
            return self._latest_by_module_type.get((module_id, artifact_type))

    def get_history(
        self,
        module_id: str | None = None,
        artifact_type: ArtifactType | None = None,
        *,
        since_sequence: int | None = None,
        limit: int | None = None,
        filters: ArtifactFilter | None = None,
    ) -> list[Artifact]:
        if artifact_type is not None and not isinstance(artifact_type, ArtifactType):
            artifact_type = ArtifactType(str(artifact_type).upper())

        with self._lock:
            history_snapshot = list(self._history)
            minimum_sequence = history_snapshot[0].sequence if history_snapshot else None
            store = self._store

        if (
            store
            and since_sequence is not None
            and minimum_sequence is not None
            and since_sequence < minimum_sequence
        ):
            from_store = store.load_since(
                since_sequence=since_sequence,
                module_id=module_id,
                artifact_type=artifact_type,
                limit=limit,
            )
            if filters is None:
                return from_store
            return [artifact for artifact in from_store if filters.matches(artifact)]

        artifacts: list[Artifact] = []
        for artifact in history_snapshot:
            if module_id and artifact.module_id != module_id:
                continue
            if artifact_type and artifact.artifact_type != artifact_type:
                continue
            if since_sequence is not None and (artifact.sequence or -1) <= since_sequence:
                continue
            if filters and not filters.matches(artifact):
                continue
            artifacts.append(artifact)

        if limit is not None and len(artifacts) > limit:
            artifacts = artifacts[-limit:]
        return artifacts

    def get_modules(self) -> list[str]:
        with self._lock:
            return sorted(self._latest_by_module.keys())

    def get_audit_trail(self, limit: int = 200) -> list[AuditRecord]:
        with self._lock:
            if limit <= 0:
                return []
            trail = list(self._audit_trail)
        return trail[-limit:]

    def get_error_events(self, limit: int = 50) -> list[Artifact]:
        events = self.get_history(artifact_type=ArtifactType.EVENT, limit=1000)
        filtered = [
            event
            for event in events
            if str(event.payload.get("severity", "info")).lower() in {"warning", "error"}
        ]
        if limit <= 0:
            return []
        return filtered[-limit:]

    def total_artifacts(self) -> int:
        with self._lock:
            return len(self._history)

    def get_last_sequence(self) -> int:
        with self._lock:
            return self._sequence

    def get_last_update(self) -> datetime | None:
        with self._lock:
            if not self._history:
                return None
            return self._history[-1].created_at

