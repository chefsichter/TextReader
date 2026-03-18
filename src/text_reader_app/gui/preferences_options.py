"""Shared option lists for persisted GUI preferences."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(slots=True, frozen=True)
class ReaderInfo:
    """Static description metadata for one Qwen custom voice."""

    label: str
    voice_description: str
    native_language: str


READER_INFO: dict[str, ReaderInfo] = {
    "vivian": ReaderInfo(
        label="Vivian",
        voice_description="Bright, slightly edgy young female voice.",
        native_language="Chinese",
    ),
    "serena": ReaderInfo(
        label="Serena",
        voice_description="Warm, gentle young female voice.",
        native_language="Chinese",
    ),
    "uncle_fu": ReaderInfo(
        label="Uncle_Fu",
        voice_description="Seasoned male voice with a low, mellow timbre.",
        native_language="Chinese",
    ),
    "dylan": ReaderInfo(
        label="Dylan",
        voice_description="Youthful Beijing male voice with a clear, natural timbre.",
        native_language="Chinese (Beijing Dialect)",
    ),
    "eric": ReaderInfo(
        label="Eric",
        voice_description="Lively Chengdu male voice with a slightly husky brightness.",
        native_language="Chinese (Sichuan Dialect)",
    ),
    "ryan": ReaderInfo(
        label="Ryan",
        voice_description="Dynamic male voice with strong rhythmic drive.",
        native_language="English",
    ),
    "aiden": ReaderInfo(
        label="Aiden",
        voice_description="Sunny American male voice with a clear midrange.",
        native_language="English",
    ),
    "ono_anna": ReaderInfo(
        label="Ono_Anna",
        voice_description="Playful Japanese female voice with a light, nimble timbre.",
        native_language="Japanese",
    ),
    "sohee": ReaderInfo(
        label="Sohee",
        voice_description="Warm Korean female voice with rich emotion.",
        native_language="Korean",
    ),
}


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


def reader_info_text(reader: str) -> str:
    """Return a human-friendly info string for one reader."""

    info = READER_INFO.get(reader.strip().lower())
    if info is None:
        return ""
    return f"{info.label}: {info.voice_description} Native language: {info.native_language}"


def language_info_text(language: str) -> str:
    """Return a human-friendly info string for one synthesis language."""

    normalized = language.strip()
    if not normalized:
        return ""
    if normalized.lower() == "auto":
        return "Synthesis language: Auto detect."
    return f"Synthesis language: {format_preference_label(normalized)}"
