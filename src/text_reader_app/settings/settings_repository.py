"""SQLite-backed settings storage."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from text_reader_app.domain.models import AppSetting


class SettingsRepository:
    """Persist and retrieve global application settings."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def initialize(self) -> None:
        """Create the settings table if it does not exist."""

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get(self, key: str) -> AppSetting | None:
        """Return a setting by key, if present."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT key, value, updated_at
                FROM app_settings
                WHERE key = ?
                """,
                (key,),
            ).fetchone()

        if row is None:
            return None
        return self._setting_from_row(row)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """Return a setting value or the provided default."""

        setting = self.get(key)
        if setting is None:
            return default
        return setting.value

    def set(self, key: str, value: str) -> AppSetting:
        """Insert or update a setting value."""

        updated_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, updated_at.isoformat()),
            )

        return AppSetting(key=key, value=value, updated_at=updated_at)

    def list_all(self) -> list[AppSetting]:
        """Return all settings ordered by key."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT key, value, updated_at
                FROM app_settings
                ORDER BY key
                """
            ).fetchall()

        return [self._setting_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._database_path)

    def _setting_from_row(self, row: sqlite3.Row | tuple[str, str, str]) -> AppSetting:
        return AppSetting(
            key=row[0],
            value=row[1],
            updated_at=datetime.fromisoformat(row[2]),
        )
