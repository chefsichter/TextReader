"""Load bundled GUI assets for the TextReader application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def load_stylesheet(theme: str = "light") -> str:
    """Return the QSS stylesheet for the given theme ('light' or 'dark')."""

    filename = "style_dark.qss" if theme == "dark" else "style_light.qss"
    qss_path = Path(__file__).parent / filename
    if not qss_path.exists():
        return ""
    return qss_path.read_text(encoding="utf-8")


def apply_stylesheet(theme: str = "light") -> None:
    """Apply the stylesheet for the given theme to the running QApplication."""

    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(load_stylesheet(theme))


def load_app_icon() -> QIcon:
    """Return the bundled application icon, or an empty QIcon as fallback."""

    icon_path = Path(__file__).parent / "icon.svg"
    if not icon_path.exists():
        return QIcon()
    return QIcon(str(icon_path))
