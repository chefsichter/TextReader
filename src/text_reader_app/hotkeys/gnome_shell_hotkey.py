"""GNOME Shell-backed global hotkey registration."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from .global_shortcut_portal import (
    GlobalShortcutPortalStatus,
    GlobalShortcutRegistration,
    ShortcutCallback,
)


GNOME_SHELL_BUS_NAME = "org.gnome.Shell"
GNOME_SHELL_OBJECT_PATH = "/org/gnome/Shell"
GNOME_SHELL_INTERFACE = "org.gnome.Shell"
GNOME_SHELL_ACTION_MODE_NORMAL = 1
GNOME_SHELL_GRAB_FLAGS_NONE = 0


class _BackendNotAvailableError(RuntimeError):
    """Raised when GNOME Shell is not reachable on the session bus."""


class _BackendRequestError(RuntimeError):
    """Raised when GNOME Shell rejects a DBus request."""


class GnomeShellHotkeyService:
    """Register one global shortcut through GNOME Shell's DBus API."""

    def __init__(
        self,
        application_name: str | None = None,
        preferred_trigger: str = "Alt+L",
        on_activated: ShortcutCallback | None = None,
    ) -> None:
        self._application_name = application_name or "TextReader"
        self._preferred_trigger = preferred_trigger
        self._callback: ShortcutCallback | None = on_activated
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bus: Any | None = None
        self._action_id: int | None = None
        self._startup_event = threading.Event()
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
            message="GNOME Shell hotkey service has not been started.",
        )

    @property
    def registration(self) -> GlobalShortcutRegistration:
        """Return the current hotkey registration state."""

        return self._registration

    def start(
        self,
        callback: ShortcutCallback | None = None,
        preferred_trigger: str | None = None,
    ) -> GlobalShortcutRegistration:
        """Start the background GNOME Shell hotkey loop."""

        if self._thread is not None:
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
        if not _dbus_next_available():
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="dbus-next is not installed in the active environment.",
            )
            return self._registration

        self._startup_event.clear()
        self._thread = threading.Thread(
            target=self._run_background_loop,
            args=(self._preferred_trigger,),
            daemon=True,
            name="textreader-hotkey-gnome-shell",
        )
        self._thread.start()
        self._startup_event.wait(timeout=5)
        return self._registration

    def stop(self) -> None:
        """Stop the background loop and ungrab the accelerator."""

        loop = self._loop
        thread = self._thread
        if loop is None or thread is None:
            return
        if not thread.is_alive():
            return
        if not loop.is_running() or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._schedule_shutdown)
        thread.join(timeout=2)

    def _run_background_loop(self, preferred_trigger: str) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            should_run = loop.run_until_complete(
                self._register_shortcut(preferred_trigger),
            )
            if should_run:
                loop.run_forever()
        except _BackendNotAvailableError as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message=str(exc),
            )
            self._startup_event.set()
        except _BackendRequestError as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=str(exc),
            )
            self._startup_event.set()
        except Exception as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=f"GNOME Shell hotkey backend failed: {exc}",
            )
            self._startup_event.set()
        finally:
            loop.run_until_complete(self._shutdown_bus())
            loop.close()
            self._loop = None
            self._thread = None

    async def _register_shortcut(self, preferred_trigger: str) -> bool:
        from dbus_next.aio import MessageBus

        self._bus = await MessageBus().connect()
        introspection_xml = await self._read_introspection_xml()
        if GNOME_SHELL_INTERFACE not in introspection_xml:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="org.gnome.Shell does not expose the accelerator API.",
            )
            self._startup_event.set()
            return False

        self._action_id = await self._grab_accelerator(preferred_trigger)
        if self._action_id == 0:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=f"GNOME Shell rejected the requested accelerator '{preferred_trigger}'.",
            )
            self._startup_event.set()
            return False

        self._bus.add_message_handler(self._handle_signal_message)
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.READY,
            message=f"{self._application_name} GNOME Shell hotkey registered.",
            trigger_description=preferred_trigger,
        )
        self._startup_event.set()
        return True

    async def _read_introspection_xml(self) -> str:
        from dbus_next import Message, MessageType

        reply = await self._bus.call(
            Message(
                destination=GNOME_SHELL_BUS_NAME,
                path=GNOME_SHELL_OBJECT_PATH,
                interface="org.freedesktop.DBus.Introspectable",
                member="Introspect",
            ),
        )
        if reply.message_type == MessageType.ERROR:
            self._raise_not_available(reply, "GNOME Shell is not available on the session bus.")
        return str(reply.body[0])

    async def _grab_accelerator(self, preferred_trigger: str) -> int:
        from dbus_next import Message, MessageType

        reply = await self._bus.call(
            Message(
                destination=GNOME_SHELL_BUS_NAME,
                path=GNOME_SHELL_OBJECT_PATH,
                interface=GNOME_SHELL_INTERFACE,
                member="GrabAccelerator",
                signature="suu",
                body=[
                    preferred_trigger,
                    GNOME_SHELL_ACTION_MODE_NORMAL,
                    GNOME_SHELL_GRAB_FLAGS_NONE,
                ],
            ),
        )
        if reply.message_type == MessageType.ERROR:
            if getattr(reply, "error_name", "") == "org.freedesktop.DBus.Error.AccessDenied":
                raise _BackendNotAvailableError(
                    "GNOME Shell does not allow external GrabAccelerator registration on this desktop.",
                )
            self._raise_error(reply, "GrabAccelerator failed.")
        return int(reply.body[0])

    async def _ungrab_accelerator(self) -> None:
        from dbus_next import Message

        if self._bus is None or self._action_id is None:
            return
        await self._bus.call(
            Message(
                destination=GNOME_SHELL_BUS_NAME,
                path=GNOME_SHELL_OBJECT_PATH,
                interface=GNOME_SHELL_INTERFACE,
                member="UngrabAccelerator",
                signature="u",
                body=[self._action_id],
            ),
        )
        self._action_id = None

    def _handle_signal_message(self, message: Any) -> bool:
        if message.path != GNOME_SHELL_OBJECT_PATH:
            return False
        if message.interface != GNOME_SHELL_INTERFACE:
            return False
        if message.member != "AcceleratorActivated":
            return False
        self._dispatch_accelerator_signal(message.body)
        return False

    def _dispatch_accelerator_signal(self, body: list[Any]) -> None:
        if not body:
            return
        action = body[0]
        parameters = body[1] if len(body) > 1 else {}
        self._on_accelerator_activated(action, parameters)

    def _on_accelerator_activated(self, action: int, _parameters: dict[str, Any]) -> None:
        if self._action_id != action or self._callback is None:
            return
        try:
            self._callback()
        except Exception:
            return

    def _schedule_shutdown(self) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.create_task(self._shutdown_and_stop())

    async def _shutdown_and_stop(self) -> None:
        await self._shutdown_bus()
        if self._loop is not None:
            self._loop.stop()

    async def _shutdown_bus(self) -> None:
        if self._bus is None:
            return
        try:
            await self._ungrab_accelerator()
        finally:
            self._bus.disconnect()
            self._bus = None

    def _raise_not_available(self, reply: Any, fallback_message: str) -> None:
        raise _BackendNotAvailableError(_message_from_reply(reply, fallback_message))

    def _raise_error(self, reply: Any, fallback_message: str) -> None:
        raise _BackendRequestError(_message_from_reply(reply, fallback_message))


def _dbus_next_available() -> bool:
    try:
        import dbus_next  # noqa: F401
    except ImportError:
        return False
    return True


def _message_from_reply(reply: Any, fallback_message: str) -> str:
    if not getattr(reply, "body", None):
        return fallback_message
    if len(reply.body) > 1:
        return str(reply.body[1])
    return str(reply.body[0])
