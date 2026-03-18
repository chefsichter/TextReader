"""Best-effort Linux selection reader backed by desktop tools and Qt."""

from __future__ import annotations

import os
import shutil
import subprocess

from PySide6.QtGui import QClipboard

from .selection_capture_common import (
    SelectionCaptureError,
    SelectionContent,
    SelectionUnsupportedError,
    require_qt_application,
)


class LinuxSelectionReader:
    """Read the current Linux text selection when the session exposes one."""

    def read_text(self) -> SelectionContent:
        """Return trimmed selection text or raise a descriptive error."""

        text = self._read_with_external_tool()
        if text:
            return SelectionContent(text=text)

        clipboard = require_qt_application().clipboard()
        if not clipboard.supportsSelection():
            self._raise_unsupported()
        text = clipboard.text(QClipboard.Mode.Selection).strip()
        if not text:
            msg = "No readable text is currently available in the Linux selection."
            raise SelectionCaptureError(msg)
        return SelectionContent(text=text)

    def _read_with_external_tool(self) -> str:
        for command in _candidate_commands():
            text = _run_capture_command(command)
            if text:
                return text
        return ""

    def _raise_unsupported(self) -> None:
        session = os.environ.get("XDG_SESSION_TYPE", "unknown")
        if session == "wayland":
            msg = (
                "This Linux session does not expose a readable primary selection. "
                "Wayland selection capture is only available when the compositor "
                "and focused app publish it to Qt."
            )
            raise SelectionUnsupportedError(msg)
        msg = "This Linux session does not expose a readable primary selection."
        raise SelectionUnsupportedError(msg)


def _candidate_commands() -> list[list[str]]:
    session = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    commands: list[list[str]] = []
    if session == "wayland" and shutil.which("wl-paste"):
        commands.append(["wl-paste", "--no-newline", "--primary"])
    if shutil.which("xclip"):
        commands.append(["xclip", "-o", "-selection", "primary", "-rmlastnl"])
    return commands


def _run_capture_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()
