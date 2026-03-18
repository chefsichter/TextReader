"""Orchestrate text capture from clipboard or selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import sys

from .clipboard_reader import ClipboardReader
from .linux_selection_reader import LinuxSelectionReader
from .selection_capture_common import SelectionCaptureError
from .windows_selection_reader import WindowsSelectionReader


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

    def __init__(
        self,
        clipboard_reader: ClipboardReader | None = None,
        linux_selection_reader: LinuxSelectionReader | None = None,
        windows_selection_reader: WindowsSelectionReader | None = None,
    ) -> None:
        self._clipboard_reader = clipboard_reader or ClipboardReader()
        self._linux_selection_reader = linux_selection_reader or LinuxSelectionReader()
        self._windows_selection_reader = windows_selection_reader or WindowsSelectionReader()

    def capture(self, mode: CaptureMode | str) -> CapturedText:
        """Read text for the requested mode or raise a clear error."""

        normalized_mode = self._normalize_mode(mode)
        if normalized_mode == CaptureMode.CLIPBOARD:
            return self._capture_clipboard()
        if normalized_mode == CaptureMode.SELECTION:
            return self._capture_selection()
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

    def _capture_selection(self) -> CapturedText:
        try:
            selection_content = self._selection_reader().read_text()
        except SelectionCaptureError as exc:
            msg = f"Selection capture failed: {exc}"
            raise TextCaptureError(msg) from exc

        return CapturedText(
            source_type=selection_content.source_type,
            text=selection_content.text,
        )

    def _selection_reader(self) -> LinuxSelectionReader | WindowsSelectionReader:
        if sys.platform == "win32":
            return self._windows_selection_reader
        return self._linux_selection_reader

    def _normalize_mode(self, mode: CaptureMode | str) -> CaptureMode:
        if isinstance(mode, CaptureMode):
            return mode

        try:
            return CaptureMode(mode)
        except ValueError as exc:
            msg = f"Unsupported capture mode: {mode!r}"
            raise TextCaptureError(msg) from exc
