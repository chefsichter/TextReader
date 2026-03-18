"""Shared types and errors for best-effort selection capture."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication


@dataclass(slots=True, frozen=True)
class SelectionContent:
    """Selection text plus small source metadata."""

    text: str
    source_type: str = "selection"


class SelectionCaptureError(RuntimeError):
    """Raised when selection capture fails for the current request."""


class SelectionUnsupportedError(SelectionCaptureError):
    """Raised when the platform cannot support the requested selection read."""


def require_qt_application() -> QApplication:
    """Return the active Qt application or raise a clear error."""

    app = QApplication.instance()
    if app is None:
        msg = "QApplication must exist before reading a text selection."
        raise SelectionCaptureError(msg)
    return app

