"""Load bundled GUI assets for the TextReader application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def load_stylesheet(theme: str = "light") -> str:
    """Return the QSS stylesheet for the given theme ('light' or 'dark')."""

    filename = "style_dark.qss" if theme == "dark" else "style_light.qss"
    qss_path = Path(__file__).parent / filename
    if not qss_path.exists():
        return ""
    gui_dir = str(Path(__file__).parent).replace("\\", "/")
    return qss_path.read_text(encoding="utf-8").replace("{{GUI_DIR}}", gui_dir)


def apply_stylesheet(theme: str = "light") -> None:
    """Apply the stylesheet for the given theme to the running QApplication."""

    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(load_stylesheet(theme))


def load_app_icon() -> QIcon:
    """Render the bundled SVG icon to pixmaps at standard sizes and return a QIcon."""

    icon_path = Path(__file__).parent / "icon.svg"
    if not icon_path.exists():
        return QIcon()

    renderer = QSvgRenderer(str(icon_path))
    if not renderer.isValid():
        return QIcon(str(icon_path))

    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
