"""Cross-platform keyboard hook service based on the hotkey-transcriber approach."""

from __future__ import annotations

import sys
import threading
from typing import Any

from .global_shortcut_portal import (
    GlobalShortcutPortalStatus,
    GlobalShortcutRegistration,
    ShortcutCallback,
)
from .trigger_parser import HotkeyTrigger, parse_hotkey_trigger


if sys.platform == "linux":
    import glob
    import os
    import select

    import evdev
    from evdev import ecodes

    _EVDEV_MODIFIER_CODES = {
        "alt": {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT},
        "ctrl": {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL},
        "shift": {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT},
        "meta": {ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA},
    }
    _KB_MARKERS = {
        ecodes.KEY_A,
        ecodes.KEY_Z,
        ecodes.KEY_SPACE,
        ecodes.KEY_ENTER,
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_LEFTALT,
    }


class KeyboardHookHotkeyService:
    """Run one global hotkey listener on Linux or Windows."""

    def __init__(
        self,
        application_name: str | None = None,
        preferred_trigger: str = "Alt+L",
        on_activated: ShortcutCallback | None = None,
    ) -> None:
        self._application_name = application_name or "TextReader"
        self._trigger = parse_hotkey_trigger(preferred_trigger)
        self._callback = on_activated
        self._thread: threading.Thread | None = None
        self._startup_event = threading.Event()
        self._stop_event = threading.Event()
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
            message="Keyboard hook service has not been started.",
        )
        self._thread_id: int | None = None
        self._hook_id: Any | None = None
        self._hook_proc: Any | None = None
        self._stop_pipe: tuple[int, int] | None = None

    @property
    def registration(self) -> GlobalShortcutRegistration:
        return self._registration

    def start(
        self,
        callback: ShortcutCallback | None = None,
        preferred_trigger: str | None = None,
    ) -> GlobalShortcutRegistration:
        if callback is not None:
            self._callback = callback
        if preferred_trigger is not None:
            self._trigger = parse_hotkey_trigger(preferred_trigger)
        if self._callback is None:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message="No activation callback was provided for the hotkey service.",
            )
            return self._registration
        if self._thread is not None and self._thread.is_alive():
            return self._registration

        self._startup_event.clear()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_backend,
            daemon=True,
            name="textreader-hotkey-hook",
        )
        self._thread.start()
        self._startup_event.wait(timeout=5)
        return self._registration

    def stop(self) -> None:
        self._stop_event.set()
        self._signal_linux_stop()
        if sys.platform == "win32":
            self._stop_windows_listener()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def restart(self, preferred_trigger: str) -> GlobalShortcutRegistration:
        """Restart the backend with an updated trigger."""

        self.stop()
        return self.start(preferred_trigger=preferred_trigger)

    def _run_backend(self) -> None:
        try:
            if sys.platform == "linux":
                self._run_linux_listener()
                return
            if sys.platform == "win32":
                self._run_windows_listener()
                return
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message=f"Keyboard hook hotkeys are not implemented for {sys.platform}.",
            )
            self._startup_event.set()
        except Exception as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=f"Keyboard hook hotkey backend failed: {exc}",
                trigger_description=self._trigger.label,
            )
            self._startup_event.set()

    def _emit_callback(self) -> None:
        if self._callback is None:
            return
        threading.Thread(target=self._callback, daemon=True).start()

    def _run_linux_listener(self) -> None:
        device = _find_keyboard_device()
        trigger_key = _evdev_key_code(self._trigger.key)
        modifier_sets = [
            _EVDEV_MODIFIER_CODES[modifier]
            for modifier in self._trigger.modifiers
            if modifier in _EVDEV_MODIFIER_CODES
        ]
        held: set[int] = set()
        pressed = False
        stop_r, stop_w = os.pipe()
        self._stop_pipe = (stop_r, stop_w)
        modifier_codes = set().union(*modifier_sets) if modifier_sets else set()
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.READY,
            message=f"{self._application_name} keyboard hook registered.",
            trigger_description=self._trigger.label,
        )
        self._startup_event.set()
        try:
            while not self._stop_event.is_set():
                ready, _, _ = select.select([device.fd, stop_r], [], [])
                if stop_r in ready:
                    break
                for event in device.read():
                    if event.type != ecodes.EV_KEY:
                        continue
                    if event.code in modifier_codes:
                        _update_held_modifiers(held, event.code, event.value)
                    if event.code != trigger_key:
                        continue
                    if event.value in (1, 2) and _modifiers_held(held, modifier_sets) and not pressed:
                        pressed = True
                        self._emit_callback()
                    if event.value == 0:
                        pressed = False
        finally:
            self._stop_pipe = None
            for fd in (stop_r, stop_w):
                try:
                    os.close(fd)
                except OSError:
                    pass
            device.close()

    def _run_windows_listener(self) -> None:
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        trigger_vk = _windows_virtual_key(self._trigger.key)
        modifier_sets = _windows_modifier_sets(self._trigger)
        held: set[int] = set()
        pressed = False

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", ctypes.wintypes.DWORD),
                ("scanCode", ctypes.wintypes.DWORD),
                ("flags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        hook_type = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        )

        def callback(n_code: int, w_param: int, l_param: int) -> int:
            nonlocal pressed
            if n_code < 0:
                return user32.CallNextHookEx(self._hook_id, n_code, w_param, l_param)
            keyboard = KBDLLHOOKSTRUCT.from_address(l_param)
            vk = keyboard.vkCode
            is_down = w_param in (0x0100, 0x0104)
            is_up = w_param in (0x0101, 0x0105)
            if vk in _windows_all_modifier_codes(modifier_sets):
                if is_down:
                    held.add(vk)
                elif is_up:
                    held.discard(vk)
            if vk == trigger_vk:
                if is_down and _windows_modifiers_held(held, modifier_sets) and not pressed:
                    pressed = True
                    self._emit_callback()
                    return 1
                if is_up:
                    pressed = False
                    return 1
            return user32.CallNextHookEx(self._hook_id, n_code, w_param, l_param)

        self._hook_proc = hook_type(callback)
        self._thread_id = kernel32.GetCurrentThreadId()
        self._hook_id = user32.SetWindowsHookExW(13, self._hook_proc, None, 0)
        if not self._hook_id:
            raise RuntimeError(f"SetWindowsHookExW failed (error {ctypes.get_last_error()})")

        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.READY,
            message=f"{self._application_name} keyboard hook registered.",
            trigger_description=self._trigger.label,
        )
        self._startup_event.set()
        message = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnhookWindowsHookEx(self._hook_id)
        self._hook_id = None
        self._thread_id = None

    def _stop_windows_listener(self) -> None:
        if self._thread_id is None:
            return
        import ctypes

        ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)

    def _signal_linux_stop(self) -> None:
        if sys.platform != "linux":
            return
        if self._stop_pipe is None:
            return
        _, stop_w = self._stop_pipe
        try:
            os.write(stop_w, b"\x00")
        except OSError:
            return


def _modifiers_held(held: set[int], modifier_sets: list[set[int]]) -> bool:
    return all(code_set & held for code_set in modifier_sets)


def _update_held_modifiers(held: set[int], code: int, value: int) -> None:
    if value in (1, 2):
        held.add(code)
        return
    if value == 0:
        held.discard(code)


if sys.platform == "linux":
    def _evdev_key_code(key: str) -> int:
        attribute = f"KEY_{key.upper()}"
        code = getattr(ecodes, attribute, None)
        if code is None:
            raise ValueError(f"Unknown key for evdev: {key!r}")
        return code


    def _score_keyboard(device: evdev.InputDevice) -> int:
        keys = set(device.capabilities().get(ecodes.EV_KEY, []))
        if len(keys & _KB_MARKERS) < 2:
            return 0
        score = len(keys & _KB_MARKERS) * 10
        name = (device.name or "").lower()
        if any(token in name for token in ("keyboard", "kbd", "keys")):
            score += 50
        if any(token in name for token in ("input-remapper", "espanso", "virtual")):
            score -= 40
        if ecodes.BTN_MOUSE in keys:
            score -= 20
        real_kbd_paths = {
            os.path.realpath(path)
            for path in glob.glob("/dev/input/by-path/*-event-kbd")
        }
        if device.path in real_kbd_paths:
            score += 100
        if device.phys:
            score += 30
        return score


    def _find_keyboard_device() -> evdev.InputDevice:
        seen: set[str] = set()
        best_device: evdev.InputDevice | None = None
        best_score = 0
        for source in (sorted(evdev.list_devices()), sorted(glob.glob("/dev/input/event*"))):
            for path in source:
                real = os.path.realpath(path)
                if real in seen:
                    continue
                seen.add(real)
                try:
                    device = evdev.InputDevice(real)
                except (FileNotFoundError, PermissionError, OSError):
                    continue
                score = _score_keyboard(device)
                if score > best_score:
                    if best_device is not None:
                        best_device.close()
                    best_device = device
                    best_score = score
                else:
                    device.close()
        if best_device is None:
            raise FileNotFoundError(
                "No usable keyboard device was found under /dev/input/event*.",
            )
        return best_device


def _windows_modifier_sets(trigger: HotkeyTrigger) -> list[set[int]]:
    mapping = {
        "alt": {0x12, 0xA4, 0xA5},
        "ctrl": {0x11, 0xA2, 0xA3},
        "shift": {0x10, 0xA0, 0xA1},
        "meta": {0x5B, 0x5C},
    }
    return [mapping[modifier] for modifier in trigger.modifiers if modifier in mapping]


def _windows_all_modifier_codes(modifier_sets: list[set[int]]) -> set[int]:
    return set().union(*modifier_sets) if modifier_sets else set()


def _windows_modifiers_held(held: set[int], modifier_sets: list[set[int]]) -> bool:
    return all(modifier_set & held for modifier_set in modifier_sets)


def _windows_virtual_key(key: str) -> int:
    function_keys = {f"f{index}": 0x6F + index for index in range(1, 13)}
    if key.lower() in function_keys:
        return function_keys[key.lower()]
    return ord(key.upper())
