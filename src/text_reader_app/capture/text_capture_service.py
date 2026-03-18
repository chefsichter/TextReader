"""Orchestrate text capture from clipboard or selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .clipboard_reader import ClipboardReader


class CaptureMode(StrEnum):
    """Supported capture modes for the current app slice."""

    CLIPBOARD = "clipboard"
    SELECTION = "selection"


class TextCaptureError(RuntimeError):
    """Raised when a configured text source cannot be read."""


@dataclass(slots=True, frozen=True)
class CapturedText:
    """Normalized captured text returned to the app layer."""

    source_type: str
    text: str


class TextCaptureService:
    """Small orchestration layer for reading the configured text source."""

    def __init__(self, clipboard_reader: ClipboardReader | None = None) -> None:
        self._clipboard_reader = clipboard_reader or ClipboardReader()

    def capture(self, mode: CaptureMode | str) -> CapturedText:
        """Read text for the requested mode or raise a clear error."""

        normalized_mode = self._normalize_mode(mode)
        if normalized_mode == CaptureMode.CLIPBOARD:
            return self._capture_clipboard()
        if normalized_mode == CaptureMode.SELECTION:
            msg = "Selection capture is not implemented yet on this platform slice."
            raise TextCaptureError(msg)
        msg = f"Unsupported capture mode: {mode!r}"
        raise TextCaptureError(msg)

    def capture_clipboard(self) -> CapturedText:
        """Convenience wrapper for clipboard mode."""

        return self._capture_clipboard()

    def capture_selection(self) -> CapturedText:
        """Explicit selection entry point for future wiring."""

        return self.capture(CaptureMode.SELECTION)

    def _capture_clipboard(self) -> CapturedText:
        try:
            clipboard_content = self._clipboard_reader.read_text()
        except (RuntimeError, ValueError) as exc:
            msg = f"Clipboard capture failed: {exc}"
            raise TextCaptureError(msg) from exc

        return CapturedText(
            source_type=clipboard_content.source_type,
            text=clipboard_content.text,
        )

    def _normalize_mode(self, mode: CaptureMode | str) -> CaptureMode:
        if isinstance(mode, CaptureMode):
            return mode

        try:
            return CaptureMode(mode)
        except ValueError as exc:
            msg = f"Unsupported capture mode: {mode!r}"
            raise TextCaptureError(msg) from exc
