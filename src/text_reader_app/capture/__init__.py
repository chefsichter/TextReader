"""Capture exports for reading source text into the app."""

from .clipboard_reader import ClipboardContent, ClipboardReader
from .linux_selection_reader import LinuxSelectionReader
from .selection_capture_common import (
    SelectionCaptureError,
    SelectionContent,
    SelectionUnsupportedError,
)
from .text_capture_service import (
    CaptureMode,
    CapturedText,
    TextCaptureError,
    TextCaptureService,
)
from .windows_selection_reader import WindowsSelectionReader

__all__ = [
    "CaptureMode",
    "CapturedText",
    "ClipboardContent",
    "ClipboardReader",
    "LinuxSelectionReader",
    "SelectionCaptureError",
    "SelectionContent",
    "SelectionUnsupportedError",
    "TextCaptureError",
    "TextCaptureService",
    "WindowsSelectionReader",
]
