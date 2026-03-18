"""Windows selection reader backed by PowerShell UI Automation."""

from __future__ import annotations

import shutil
import subprocess
import sys

from .selection_capture_common import (
    SelectionCaptureError,
    SelectionContent,
    SelectionUnsupportedError,
)


class WindowsSelectionReader:
    """Expose a stable API for focused-text selection capture on Windows."""

    def read_text(self) -> SelectionContent:
        """Return selected text from the focused control when Windows permits it."""

        if sys.platform != "win32":
            msg = "Windows selection capture is only available on Windows."
            raise SelectionUnsupportedError(msg)
        if shutil.which("powershell.exe") is None:
            msg = "powershell.exe is required for Windows selection capture."
            raise SelectionUnsupportedError(msg)

        text = _read_with_powershell()
        if not text:
            msg = "No readable selected text is available in the focused Windows control."
            raise SelectionCaptureError(msg)
        return SelectionContent(text=text)


def _read_with_powershell() -> str:
    script = r"""
Add-Type -AssemblyName UIAutomationClient
$element = [System.Windows.Automation.AutomationElement]::FocusedElement
if ($null -eq $element) { return }
if ($element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$textPattern)) {
  $ranges = $textPattern.GetSelection()
  if ($ranges.Length -gt 0) {
    $text = $ranges[0].GetText(-1)
    if ($text) { Write-Output $text.Trim() }
    return
  }
}
if ($element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$valuePattern)) {
  $value = $valuePattern.Current.Value
  if ($value) { Write-Output $value.Trim() }
}
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
