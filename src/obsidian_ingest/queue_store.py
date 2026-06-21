from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .dedupe import normalize_source_key
from .platforms import detect_platform


@dataclass(frozen=True)
class QueueItem:
    id: int
    url: str
    title: str | None
    platform: str
    content_type: str
    status: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]
    note_path: str | None
    error: str | None


class QueueStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def enqueue(self, url: str, title: str | None = None, metadata: dict[str, Any] | None = None) -> QueueItem:
        now = _now()
        raw_url = url.strip()
        normalized_url = normalize_source_key(raw_url)
        item_metadata = dict(metadata or {})
        if raw_url != normalized_url:
            item_metadata.setdefault("original_source", raw_url)
        info = detect_platform(normalized_url)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO queue
                (url, title, platform, content_type, status, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (normalized_url, title, info.platform, info.content_type, now, now, json.dumps(item_metadata, ensure_ascii=False)),
            )
            if title:
                conn.execute(
                    "UPDATE queue SET updated_at = ? WHERE url = ? AND (title IS NULL OR title = '')",
                    (now, normalized_url),
                )
            row = conn.execute("SELECT * FROM queue WHERE url = ?", (normalized_url,)).fetchone()
        return _row_to_item(row)

    def list_pending(self, limit: int = 10) -> list[QueueItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM queue WHERE status = 'pending' ORDER BY id LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def list_recent(self, limit: int = 50, status: str | None = None) -> list[QueueItem]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM queue WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM queue ORDER BY id DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        return [_row_to_item(row) for row in rows]

    def count_by_status(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM queue GROUP BY status ORDER BY status",
            ).fetchall()
        counts = {"pending": 0, "processing": 0, "done": 0, "failed": 0, "skipped": 0}
        for row in rows:
            counts[str(row["status"])] = int(row["count"])
        return counts

    def get(self, item_id: int) -> QueueItem:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM queue WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(f"Queue item not found: {item_id}")
        return _row_to_item(row)

    def mark_processing(self, item_id: int) -> None:
        self._set_status(item_id, "processing")

    def mark_done(self, item_id: int, note_path: str) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE queue SET status = 'done', note_path = ?, error = NULL, updated_at = ? WHERE id = ?",
                (note_path, now, item_id),
            )

    def mark_failed(self, item_id: int, error: str) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE queue SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (error, now, item_id),
            )

    def mark_skipped(self, item_id: int, reason: str = "skipped") -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE queue SET status = 'skipped', error = ?, updated_at = ? WHERE id = ?",
                (reason, now, item_id),
            )

    def retry_item(self, item_id: int) -> QueueItem:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE queue SET status = 'pending', error = NULL, updated_at = ? WHERE id = ?",
                (now, item_id),
            )
            row = conn.execute("SELECT * FROM queue WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(f"Queue item not found: {item_id}")
        return _row_to_item(row)

    def retry_failed(self, limit: int = 50) -> int:
        now = _now()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM queue WHERE status = 'failed' ORDER BY updated_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            ids = [int(row["id"]) for row in rows]
            for item_id in ids:
                conn.execute(
                    "UPDATE queue SET status = 'pending', error = NULL, updated_at = ? WHERE id = ?",
                    (now, item_id),
                )
        return len(ids)

    def _set_status(self, item_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE queue SET status = ?, updated_at = ? WHERE id = ?", (status, _now(), item_id))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    platform TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    note_path TEXT,
                    error TEXT
                )
                """
            )


def _row_to_item(row: sqlite3.Row) -> QueueItem:
    return QueueItem(
        id=int(row["id"]),
        url=row["url"],
        title=row["title"],
        platform=row["platform"],
        content_type=row["content_type"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata=json.loads(row["metadata"] or "{}"),
        note_path=row["note_path"],
        error=row["error"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
