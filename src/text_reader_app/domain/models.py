"""Small domain models shared across the app."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class HistoryEntryStatus(StrEnum):
    """Lifecycle states for a stored text item."""

    CAPTURED = "captured"
    SYNTHESIZING = "synthesizing"
    READY = "ready"
    PLAYING = "playing"
    FAILED = "failed"


@dataclass(slots=True)
class AppSetting:
    """Single key/value application setting."""

    key: str
    value: str
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class AppPreferences:
    """Normalized persisted settings used by the runtime and GUI."""

    capture_mode: str
    hotkey_trigger: str
    jump_seconds: int
    voice: str
    language: str
    synthesis_mode: str = "whole"
    theme: str = "light"


@dataclass(slots=True)
class HistoryEntry:
    """Persisted text capture and synthesis state."""

    id: int | None
    created_at: datetime
    source_type: str
    text: str
    status: HistoryEntryStatus
    source_app: str | None = None
    error_message: str | None = None
    voice: str | None = None
    language: str | None = None
    model_id: str | None = None
    audio_path: str | None = None
    audio_duration_ms: int | None = None
    last_position_ms: int = 0

    @classmethod
    def new(
        cls,
        *,
        source_type: str,
        text: str,
        status: HistoryEntryStatus = HistoryEntryStatus.CAPTURED,
        source_app: str | None = None,
    ) -> "HistoryEntry":
        """Create a new unsaved history entry with sane defaults."""

        return cls(
            id=None,
            created_at=datetime.now(UTC),
            source_type=source_type,
            text=text,
            status=status,
            source_app=source_app,
        )
