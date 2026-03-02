"""
SQLite persistence for simulation artifacts.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

from atlas.core.analytics.artifacts import Artifact, ArtifactType


class ArtifactStore(Protocol):
    def save(self, artifact: Artifact) -> None:
        ...

    def load_recent(self, limit: int = 1000) -> list[Artifact]:
        ...

    def load_since(
        self,
        since_sequence: int,
        *,
        module_id: str | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int | None = None,
    ) -> list[Artifact]:
        ...


class SQLiteArtifactStore:
    """
    Optional persistence backend for artifacts.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), timeout=5)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    published_by TEXT NOT NULL,
                    tick INTEGER,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_sequence ON artifacts(sequence)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_module ON artifacts(module_id, sequence)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type, sequence)"
            )

    def save(self, artifact: Artifact) -> None:
        if artifact.sequence is None:
            raise ValueError("Artifact sequence must be assigned before persistence")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts (
                    artifact_id,
                    sequence,
                    artifact_type,
                    title,
                    module_id,
                    payload_json,
                    tags_json,
                    created_at,
                    published_by,
                    tick,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id,
                    artifact.sequence,
                    artifact.artifact_type.value,
                    artifact.title,
                    artifact.module_id,
                    json.dumps(artifact.payload, ensure_ascii=True),
                    json.dumps(artifact.tags, ensure_ascii=True),
                    artifact.created_at.isoformat(),
                    artifact.published_by,
                    artifact.tick,
                    json.dumps(artifact.metadata, ensure_ascii=True),
                ),
            )

    def load_recent(self, limit: int = 1000) -> list[Artifact]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT artifact_id, sequence, artifact_type, title, module_id,
                       payload_json, tags_json, created_at, published_by, tick, metadata_json
                FROM artifacts
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        artifacts = [self._row_to_artifact(row) for row in rows]
        artifacts.reverse()
        return artifacts

    def load_since(
        self,
        since_sequence: int,
        *,
        module_id: str | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int | None = None,
    ) -> list[Artifact]:
        query = (
            "SELECT artifact_id, sequence, artifact_type, title, module_id, "
            "payload_json, tags_json, created_at, published_by, tick, metadata_json "
            "FROM artifacts WHERE sequence > ?"
        )
        params: list[object] = [since_sequence]

        if module_id:
            query += " AND module_id = ?"
            params.append(module_id)

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type.value)

        query += " ORDER BY sequence ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [self._row_to_artifact(row) for row in rows]

    @staticmethod
    def _row_to_artifact(row: tuple[object, ...]) -> Artifact:
        return Artifact.from_record(
            {
                "artifact_id": row[0],
                "sequence": int(row[1]),
                "artifact_type": str(row[2]),
                "title": str(row[3]),
                "module_id": str(row[4]),
                "payload": json.loads(str(row[5])),
                "tags": json.loads(str(row[6])),
                "created_at": str(row[7]),
                "published_by": str(row[8]),
                "tick": row[9],
                "metadata": json.loads(str(row[10])),
            }
        )

