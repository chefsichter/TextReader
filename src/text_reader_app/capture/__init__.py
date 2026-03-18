"""Capture exports for reading source text into the app."""

from .clipboard_reader import ClipboardContent, ClipboardReader
from .text_capture_service import (
    CaptureMode,
    CapturedText,
    TextCaptureError,
    TextCaptureService,
)

__all__ = [
    "CaptureMode",
    "CapturedText",
    "ClipboardContent",
    "ClipboardReader",
    "TextCaptureError",
    "TextCaptureService",
]
