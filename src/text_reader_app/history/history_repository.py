"""SQLite-backed history storage."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from text_reader_app.domain.models import HistoryEntry, HistoryEntryStatus


class HistoryRepository:
    """Store captured text items and their synthesis state."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def initialize(self) -> None:
        """Create the history table if it does not exist."""

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS history_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_app TEXT,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    voice TEXT,
                    language TEXT,
                    model_id TEXT,
                    audio_path TEXT,
                    audio_duration_ms INTEGER,
                    last_position_ms INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def create(self, entry: HistoryEntry) -> HistoryEntry:
        """Insert a new history entry and return it with an id."""

        values = self._history_values(entry)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO history_entries (
                    created_at,
                    source_type,
                    source_app,
                    text,
                    status,
                    error_message,
                    voice,
                    language,
                    model_id,
                    audio_path,
                    audio_duration_ms,
                    last_position_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

        return HistoryEntry(id=cursor.lastrowid, **self._history_kwargs(entry))

    def update(self, entry: HistoryEntry) -> None:
        """Persist updates for an existing history entry."""

        if entry.id is None:
            msg = "Cannot update a history entry without an id."
            raise ValueError(msg)

        values = self._history_values(entry)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE history_entries
                SET created_at = ?,
                    source_type = ?,
                    source_app = ?,
                    text = ?,
                    status = ?,
                    error_message = ?,
                    voice = ?,
                    language = ?,
                    model_id = ?,
                    audio_path = ?,
                    audio_duration_ms = ?,
                    last_position_ms = ?
                WHERE id = ?
                """,
                (*values, entry.id),
            )

    def get(self, entry_id: int) -> HistoryEntry | None:
        """Return one history entry by id."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM history_entries
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()

        if row is None:
            return None
        return self._history_from_row(row)

    def list_recent(self, limit: int = 20) -> list[HistoryEntry]:
        """Return the most recent history entries first."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM history_entries
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._history_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _history_values(self, entry: HistoryEntry) -> tuple[object, ...]:
        return (
            entry.created_at.isoformat(),
            entry.source_type,
            entry.source_app,
            entry.text,
            entry.status.value,
            entry.error_message,
            entry.voice,
            entry.language,
            entry.model_id,
            entry.audio_path,
            entry.audio_duration_ms,
            entry.last_position_ms,
        )

    def _history_kwargs(self, entry: HistoryEntry) -> dict[str, object]:
        return {
            "created_at": entry.created_at,
            "source_type": entry.source_type,
            "source_app": entry.source_app,
            "text": entry.text,
            "status": entry.status,
            "error_message": entry.error_message,
            "voice": entry.voice,
            "language": entry.language,
            "model_id": entry.model_id,
            "audio_path": entry.audio_path,
            "audio_duration_ms": entry.audio_duration_ms,
            "last_position_ms": entry.last_position_ms,
        }

    def _history_from_row(self, row: sqlite3.Row) -> HistoryEntry:
        return HistoryEntry(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            source_type=row["source_type"],
            source_app=row["source_app"],
            text=row["text"],
            status=HistoryEntryStatus(row["status"]),
            error_message=row["error_message"],
            voice=row["voice"],
            language=row["language"],
            model_id=row["model_id"],
            audio_path=row["audio_path"],
            audio_duration_ms=row["audio_duration_ms"],
            last_position_ms=row["last_position_ms"],
        )
