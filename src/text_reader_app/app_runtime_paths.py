"""Resolve runtime directories for the local TextReader app state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass(slots=True, frozen=True)
class AppRuntimePaths:
    """Filesystem paths used by the current app slice."""

    data_directory: Path
    database_path: Path
    audio_cache_directory: Path


def build_runtime_paths(application_name: str) -> AppRuntimePaths:
    """Return normalized runtime paths for the given app name."""

    data_directory = _resolve_data_directory(application_name)
    audio_cache_directory = data_directory / "audio_cache"
    audio_cache_directory.mkdir(parents=True, exist_ok=True)
    return AppRuntimePaths(
        data_directory=data_directory,
        database_path=data_directory / "text_reader.sqlite3",
        audio_cache_directory=audio_cache_directory,
    )


def _resolve_data_directory(application_name: str) -> Path:
    app_data_location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation,
    )
    if app_data_location:
        data_directory = Path(app_data_location)
    else:
        data_directory = Path.home() / ".local" / "share" / _normalize_name(
            application_name,
        )

    data_directory.mkdir(parents=True, exist_ok=True)
    return data_directory


def _normalize_name(application_name: str) -> str:
    return application_name.strip().lower().replace(" ", "_")
