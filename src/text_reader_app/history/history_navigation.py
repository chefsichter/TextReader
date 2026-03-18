"""Navigation primitives for browsing persisted history entries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class HistoryNavigation:
    """Describe the current entry position inside the newest-first history view."""

    current_entry_id: int | None
    previous_entry_id: int | None
    next_entry_id: int | None
    current_position: int
    total_entries: int

    @property
    def has_previous(self) -> bool:
        """Return whether a previous history entry exists."""

        return self.previous_entry_id is not None

    @property
    def has_next(self) -> bool:
        """Return whether a next history entry exists."""

        return self.next_entry_id is not None

