"""Read clipboard text from the current Qt application."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication


@dataclass(slots=True, frozen=True)
class ClipboardContent:
    """Clipboard text plus a small amount of source metadata."""

    text: str
    source_type: str = "clipboard"


class ClipboardReader:
    """Read plain text from the Qt clipboard."""

    def read_text(self) -> ClipboardContent:
        """Return trimmed clipboard text or raise a descriptive error."""

        clipboard = self._get_clipboard()
        text = clipboard.text(QClipboard.Mode.Clipboard).strip()
        if not text:
            msg = "Clipboard does not contain readable text."
            raise ValueError(msg)
        return ClipboardContent(text=text)

    def _get_clipboard(self) -> QClipboard:
        app = QApplication.instance()
        if app is None:
            msg = "QApplication must exist before reading the clipboard."
            raise RuntimeError(msg)
        return app.clipboard()
