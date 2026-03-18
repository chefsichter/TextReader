"""Shared option lists for persisted GUI preferences."""

from __future__ import annotations

READER_OPTIONS: tuple[str, ...] = (
    "serena",
    "vivian",
    "uncle_fu",
    "dylan",
    "eric",
    "ryan",
    "aiden",
    "ono_anna",
    "sohee",
)

LANGUAGE_OPTIONS: tuple[str, ...] = (
    "auto",
    "chinese",
    "english",
    "japanese",
    "korean",
    "german",
    "french",
    "russian",
    "portuguese",
    "spanish",
    "italian",
)

SYNTHESIS_MODE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("whole", "Whole text"),
    ("streaming", "Streaming input (Qwen)"),
)


def build_menu_options(current_value: str, defaults: tuple[str, ...]) -> list[str]:
    """Return stable menu options with the current value inserted if needed."""

    normalized_value = current_value.strip()
    if normalized_value and normalized_value not in defaults:
        return [normalized_value, *defaults]
    return list(defaults)


def format_preference_label(value: str) -> str:
    """Return a human-friendly label for tray menu entries."""

    normalized = value.strip()
    if normalized == "auto":
        return "Auto"
    return "_".join(part.capitalize() for part in normalized.split("_") if part)


def synthesis_mode_label(mode: str) -> str:
    """Return a human-friendly label for the synthesis mode setting."""

    for value, label in SYNTHESIS_MODE_OPTIONS:
        if value == mode:
            return label
    return format_preference_label(mode)
