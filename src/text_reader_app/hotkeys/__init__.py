"""Global hotkey backends for TextReader."""

from .global_shortcut_portal import (
    GlobalShortcutPortalService,
    GlobalShortcutPortalStatus,
    GlobalShortcutRegistration,
)
from .gnome_shell_hotkey import GnomeShellHotkeyService

__all__ = [
    "GnomeShellHotkeyService",
    "GlobalShortcutPortalService",
    "GlobalShortcutPortalStatus",
    "GlobalShortcutRegistration",
]
