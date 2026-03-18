"""SQLite-backed history storage."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from text_reader_app.domain.models import HistoryEntry, HistoryEntryStatus

from .history_navigation import HistoryNavigation


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

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[HistoryEntry]:
        """Return the most recent history entries first."""

        normalized_limit = max(1, limit)
        normalized_offset = max(0, offset)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM history_entries
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                OFFSET ?
                """,
                (normalized_limit, normalized_offset),
            ).fetchall()

        return [self._history_from_row(row) for row in rows]

    def count_entries(self) -> int:
        """Return the total number of stored history entries."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS entry_count FROM history_entries",
            ).fetchone()
        return int(row["entry_count"])

    def latest(self) -> HistoryEntry | None:
        """Return the most recent history entry, if any."""

        entries = self.list_recent(limit=1)
        if not entries:
            return None
        return entries[0]

    def get_previous(self, entry_id: int) -> HistoryEntry | None:
        """Return the previous entry in newest-first history order."""

        return self._entry_for_neighbor(entry_id, offset=-1)

    def get_next(self, entry_id: int) -> HistoryEntry | None:
        """Return the next entry in newest-first history order."""

        return self._entry_for_neighbor(entry_id, offset=1)

    def describe_navigation(self, entry_id: int | None) -> HistoryNavigation:
        """Describe navigation state for one entry in newest-first order."""

        entry_ids = self._ordered_entry_ids()
        if not entry_ids:
            return HistoryNavigation(
                current_entry_id=None,
                previous_entry_id=None,
                next_entry_id=None,
                current_position=0,
                total_entries=0,
            )

        current_index = self._current_index(entry_ids, entry_id)
        return HistoryNavigation(
            current_entry_id=entry_ids[current_index],
            previous_entry_id=_entry_id_at(entry_ids, current_index - 1),
            next_entry_id=_entry_id_at(entry_ids, current_index + 1),
            current_position=current_index + 1,
            total_entries=len(entry_ids),
        )

    def update_last_position(self, entry_id: int, position_ms: int) -> None:
        """Persist the last known playback position for one history entry."""

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE history_entries
                SET last_position_ms = ?
                WHERE id = ?
                """,
                (max(0, position_ms), entry_id),
            )

    def update_playback_state(
        self,
        entry_id: int,
        *,
        position_ms: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Persist playback metadata for one entry."""

        assignments: list[str] = []
        values: list[object] = []
        if position_ms is not None:
            assignments.append("last_position_ms = ?")
            values.append(max(0, position_ms))
        if duration_ms is not None:
            assignments.append("audio_duration_ms = ?")
            values.append(max(0, duration_ms))
        if not assignments:
            return

        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE history_entries
                SET {", ".join(assignments)}
                WHERE id = ?
                """,
                (*values, entry_id),
            )

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

    def _ordered_entry_ids(self) -> list[int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id
                FROM history_entries
                ORDER BY created_at DESC, id DESC
                """,
            ).fetchall()
        return [int(row["id"]) for row in rows]

    def _entry_for_neighbor(self, entry_id: int, offset: int) -> HistoryEntry | None:
        navigation = self.describe_navigation(entry_id)
        neighbor_id = navigation.previous_entry_id if offset < 0 else navigation.next_entry_id
        if neighbor_id is None:
            return None
        return self.get(neighbor_id)

    def _current_index(self, entry_ids: list[int], entry_id: int | None) -> int:
        if entry_id is None:
            return 0
        try:
            return entry_ids.index(entry_id)
        except ValueError:
            return 0


def _entry_id_at(entry_ids: list[int], index: int) -> int | None:
    if index < 0 or index >= len(entry_ids):
        return None
    return entry_ids[index]
