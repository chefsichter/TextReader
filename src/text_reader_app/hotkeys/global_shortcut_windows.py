"""Native Windows global hotkey backend using RegisterHotKey."""

from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes

from .global_shortcut_portal import (
    GlobalShortcutPortalStatus,
    GlobalShortcutRegistration,
    ShortcutCallback,
)


WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008


class WindowsGlobalHotkeyService:
    """Register one process-owned global hotkey on Windows."""

    def __init__(
        self,
        application_name: str | None = None,
        preferred_trigger: str = "Alt+L",
        on_activated: ShortcutCallback | None = None,
    ) -> None:
        self._application_name = application_name or "TextReader"
        self._preferred_trigger = preferred_trigger
        self._callback = on_activated
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hotkey_id = 1
        self._startup_event = threading.Event()
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
            message="Windows hotkey service has not been started.",
        )

    @property
    def registration(self) -> GlobalShortcutRegistration:
        return self._registration

    def start(
        self,
        callback: ShortcutCallback | None = None,
        preferred_trigger: str | None = None,
    ) -> GlobalShortcutRegistration:
        if sys.platform != "win32":
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="Windows hotkey backend is only available on Windows.",
            )
            return self._registration
        if callback is not None:
            self._callback = callback
        if preferred_trigger is not None:
            self._preferred_trigger = preferred_trigger
        if self._callback is None:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message="No activation callback was provided for the hotkey service.",
            )
            return self._registration
        if self._thread is not None:
            return self._registration

        self._startup_event.clear()
        self._thread = threading.Thread(
            target=self._run_message_loop,
            daemon=True,
            name="textreader-hotkey-windows",
        )
        self._thread.start()
        self._startup_event.wait(timeout=5)
        return self._registration

    def stop(self) -> None:
        if self._thread_id is None:
            return
        user32 = ctypes.windll.user32
        user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run_message_loop(self) -> None:
        user32 = ctypes.windll.user32
        modifiers, virtual_key = _parse_trigger(self._preferred_trigger)
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, self._hotkey_id, modifiers, virtual_key):
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=f"Windows rejected the requested hotkey '{self._preferred_trigger}'.",
            )
            self._startup_event.set()
            return

        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.READY,
            message=f"{self._application_name} Windows hotkey registered.",
            trigger_description=self._preferred_trigger,
        )
        self._startup_event.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) != 0:
            if message.message == WM_HOTKEY and self._callback is not None:
                self._callback()
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnregisterHotKey(None, self._hotkey_id)
        self._thread = None
        self._thread_id = None


def _parse_trigger(trigger: str) -> tuple[int, int]:
    tokens = [token.strip().lower() for token in trigger.split("+") if token.strip()]
    if not tokens:
        return MOD_ALT, ord("L")

    modifiers = 0
    key_token = tokens[-1]
    for token in tokens[:-1]:
        modifiers |= {
            "alt": MOD_ALT,
            "ctrl": MOD_CONTROL,
            "control": MOD_CONTROL,
            "shift": MOD_SHIFT,
            "win": MOD_WIN,
            "meta": MOD_WIN,
        }.get(token, 0)
    return modifiers or MOD_ALT, _virtual_key(key_token)


def _virtual_key(token: str) -> int:
    if len(token) == 1:
        return ord(token.upper())
    function_keys = {
        f"f{index}": 0x6F + index
        for index in range(1, 13)
    }
    return function_keys.get(token, ord("L"))
