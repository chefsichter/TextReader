"""Public hotkey helpers used by the active TextReader runtime."""

try:
    from .keyboard_hook_service import KeyboardHookHotkeyService
except ImportError:  # pragma: no cover - depends on optional OS packages
    KeyboardHookHotkeyService = None

from .local_command_bridge import LocalCommandServer, send_local_command
from .trigger_parser import format_hotkey_trigger, parse_hotkey_trigger

__all__ = [
    "KeyboardHookHotkeyService",
    "LocalCommandServer",
    "format_hotkey_trigger",
    "parse_hotkey_trigger",
    "send_local_command",
]
