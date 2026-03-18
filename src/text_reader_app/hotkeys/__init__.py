"""Global hotkey backends for TextReader."""

from .global_shortcut_portal import (
    GlobalShortcutPortalService,
    GlobalShortcutPortalStatus,
    GlobalShortcutRegistration,
)
from .global_shortcut_windows import WindowsGlobalHotkeyService
from .gnome_shell_hotkey import GnomeShellHotkeyService
from .local_command_bridge import LocalCommandServer, send_local_command

__all__ = [
    "GnomeShellHotkeyService",
    "GlobalShortcutPortalService",
    "GlobalShortcutPortalStatus",
    "GlobalShortcutRegistration",
    "LocalCommandServer",
    "WindowsGlobalHotkeyService",
    "send_local_command",
]
