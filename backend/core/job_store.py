"""Small SQLite-backed mapping for generation jobs.

The UI polls jobs by an application job ID while ComfyUI uses its own prompt ID
internally. Persisting that mapping lets polling resume after a backend restart.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator, MutableMapping
from enum import Enum
from typing import Any

from core.runtime import JOB_DB


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class PersistentJobMap(MutableMapping[str, dict[str, Any]]):
    """A process-safe, low-volume mapping stored in one SQLite table."""

    _schema_lock = threading.Lock()

    def __init__(self, namespace: str):
        self.namespace = namespace
        self._ensure_schema()

    @staticmethod
    def _connect() -> sqlite3.Connection:
        connection = sqlite3.connect(JOB_DB, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @classmethod
    def _ensure_schema(cls) -> None:
        with cls._schema_lock, cls._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_jobs (
                    namespace TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (namespace, job_id)
                )
                """
            )

    def __getitem__(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM generation_jobs WHERE namespace = ? AND job_id = ?",
                (self.namespace, job_id),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return json.loads(row[0])

    def __setitem__(self, job_id: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, default=_json_default, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_jobs(namespace, job_id, payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(namespace, job_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (self.namespace, job_id, encoded, time.time()),
            )

    def __delitem__(self, job_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM generation_jobs WHERE namespace = ? AND job_id = ?",
                (self.namespace, job_id),
            )
        if cursor.rowcount == 0:
            raise KeyError(job_id)

    def __iter__(self) -> Iterator[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT job_id FROM generation_jobs WHERE namespace = ? ORDER BY updated_at",
                (self.namespace,),
            ).fetchall()
        return iter(row[0] for row in rows)

    def __len__(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM generation_jobs WHERE namespace = ?",
                (self.namespace,),
            ).fetchone()
        return int(row[0])

    def pop(self, key: str, default: Any = None) -> Any:
        try:
            value = self[key]
        except KeyError:
            return default
        del self[key]
        return value
