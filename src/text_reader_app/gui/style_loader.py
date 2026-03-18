"""Load bundled GUI assets for the TextReader application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


def load_stylesheet() -> str:
    """Return the contents of the bundled style.qss file."""

    qss_path = Path(__file__).parent / "style.qss"
    if not qss_path.exists():
        return ""
    return qss_path.read_text(encoding="utf-8")


def load_app_icon() -> QIcon:
    """Return the bundled application icon, or an empty QIcon as fallback."""

    icon_path = Path(__file__).parent / "icon.svg"
    if not icon_path.exists():
        return QIcon()
    return QIcon(str(icon_path))
