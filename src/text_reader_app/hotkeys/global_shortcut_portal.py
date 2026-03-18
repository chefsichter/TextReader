"""Portal-backed Linux/Wayland global shortcut registration."""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable


ShortcutCallback = Callable[[], None]

PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
PORTAL_INTERFACE = "org.freedesktop.portal.GlobalShortcuts"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
READ_ACTIVE_SOURCE_SHORTCUT_ID = "read-active-source"


class GlobalShortcutPortalStatus(StrEnum):
    """Stable status values for portal-backed global shortcuts."""

    READY = "ready"
    NOT_AVAILABLE = "not_available"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class GlobalShortcutRegistration:
    """Result returned by the portal hotkey registration flow."""

    status: GlobalShortcutPortalStatus
    message: str
    trigger_description: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether the portal registration succeeded."""

        return self.status == GlobalShortcutPortalStatus.READY


class GlobalShortcutPortalService:
    """Register one global shortcut through the XDG portal."""

    def __init__(
        self,
        application_name: str | None = None,
        preferred_trigger: str = "Alt+L",
        on_activated: ShortcutCallback | None = None,
    ) -> None:
        self._application_name = application_name or "TextReader"
        self._preferred_trigger = preferred_trigger
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bus: Any | None = None
        self._session_handle: str | None = None
        self._callback: ShortcutCallback | None = on_activated
        self._startup_event = threading.Event()
        self._registration = GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
            message="Global shortcut portal service has not been started.",
        )

    @property
    def registration(self) -> GlobalShortcutRegistration:
        """Return the current registration state."""

        return self._registration

    def start(
        self,
        callback: ShortcutCallback | None = None,
        preferred_trigger: str | None = None,
    ) -> GlobalShortcutRegistration:
        """Start the background portal flow and return the initial status."""

        if self._thread is not None:
            return self._registration

        try:
            from dbus_next import Variant  # noqa: F401
            from dbus_next.aio import MessageBus  # noqa: F401
        except ImportError:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="dbus-next is not installed in the active environment.",
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
        self._startup_event.clear()
        self._thread = threading.Thread(
            target=self._run_background_loop,
            args=(self._preferred_trigger,),
            daemon=True,
            name="textreader-hotkey-portal",
        )
        self._thread.start()
        self._startup_event.wait(timeout=5)
        return self._registration

    def stop(self) -> None:
        """Stop the background loop if the service is running."""

        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_background_loop(self, preferred_trigger: str) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._register_shortcut(preferred_trigger))
            loop.run_forever()
        except Exception as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message=f"Portal hotkey backend failed: {exc}",
            )
            self._startup_event.set()
        finally:
            loop.run_until_complete(self._shutdown_bus())
            loop.close()

    async def _register_shortcut(self, preferred_trigger: str) -> None:
        from dbus_next.aio import MessageBus

        self._bus = await MessageBus().connect()
        try:
            introspection_xml = await self._read_introspection_xml()
            version = await self._read_portal_version()
        except Exception as exc:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message=f"Global shortcuts portal is not introspectable: {exc}",
            )
            self._startup_event.set()
            return
        if PORTAL_INTERFACE not in introspection_xml:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="Global shortcuts portal is not exposed by the current desktop.",
            )
            self._startup_event.set()
            return
        if version < 2:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.NOT_AVAILABLE,
                message="Global shortcuts portal version 2 is not available.",
            )
            self._startup_event.set()
            return

        self._bus.add_message_handler(self._handle_signal_message)
        self._session_handle = await self._create_session()
        if self._session_handle is None:
            self._startup_event.set()
            return
        self._registration = await self._bind_shortcut(preferred_trigger)
        self._startup_event.set()

    async def _read_introspection_xml(self) -> str:
        from dbus_next import Message, MessageType

        reply = await self._bus.call(
            Message(
                destination=PORTAL_BUS_NAME,
                path=PORTAL_OBJECT_PATH,
                interface="org.freedesktop.DBus.Introspectable",
                member="Introspect",
            ),
        )
        if reply.message_type == MessageType.ERROR:
            raise RuntimeError(reply.body[0] if reply.body else "Introspect call failed.")
        return str(reply.body[0])

    async def _call_portal_method(
        self,
        member: str,
        signature: str = "",
        body: list[Any] | None = None,
    ) -> Any:
        from dbus_next import Message, MessageType

        reply = await self._bus.call(
            Message(
                destination=PORTAL_BUS_NAME,
                path=PORTAL_OBJECT_PATH,
                interface=PORTAL_INTERFACE,
                member=member,
                signature=signature,
                body=body or [],
            ),
        )
        if reply.message_type == MessageType.ERROR:
            raise RuntimeError(reply.body[0] if reply.body else f"{member} call failed.")
        return reply

    async def _read_portal_version(self) -> int:
        from dbus_next import Message, MessageType

        reply = await self._bus.call(
            Message(
                destination=PORTAL_BUS_NAME,
                path=PORTAL_OBJECT_PATH,
                interface="org.freedesktop.DBus.Properties",
                member="Get",
                signature="ss",
                body=[PORTAL_INTERFACE, "version"],
            ),
        )
        if reply.message_type == MessageType.ERROR:
            raise RuntimeError(reply.body[0] if reply.body else "Get(version) failed.")
        return int(reply.body[0].value)

    async def _create_session(self) -> str | None:
        from dbus_next import Variant

        token = _make_token("gs")
        session_token = _make_token("session")
        request_path = _request_path_for_bus(self._bus.unique_name, token)
        response_future = self._create_response_future(request_path)
        await self._call_portal_method(
            member="CreateSession",
            signature="a{sv}",
            body=[
                {
                    "handle_token": Variant("s", token),
                    "session_handle_token": Variant("s", session_token),
                },
            ],
        )
        response_code, response_results = await response_future
        if response_code != 0:
            self._registration = GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message="Portal denied the global shortcut session request.",
            )
            return None
        session_handle = response_results.get("session_handle")
        if hasattr(session_handle, "value"):
            return str(session_handle.value)
        return str(session_handle)

    async def _bind_shortcut(
        self,
        preferred_trigger: str,
    ) -> GlobalShortcutRegistration:
        from dbus_next import Variant

        token = _make_token("bind")
        request_path = _request_path_for_bus(self._bus.unique_name, token)
        response_future = self._create_response_future(request_path)
        await self._call_portal_method(
            member="BindShortcuts",
            signature="oa(sa{sv})sa{sv}",
            body=[
                self._session_handle,
                [
                    (
                        READ_ACTIVE_SOURCE_SHORTCUT_ID,
                        {
                            "description": Variant(
                                "s",
                                "Read the currently active source aloud.",
                            ),
                            "preferred_trigger": Variant("s", preferred_trigger),
                        },
                    ),
                ],
                "",
                {"handle_token": Variant("s", token)},
            ],
        )
        response_code, response_results = await response_future
        if response_code != 0:
            return GlobalShortcutRegistration(
                status=GlobalShortcutPortalStatus.ERROR,
                message="Portal shortcut binding was rejected or cancelled.",
            )
        return _registration_from_response(response_results)

    def _handle_signal_message(self, message: Any) -> bool:
        if message.path != PORTAL_OBJECT_PATH:
            return False
        if message.interface != PORTAL_INTERFACE or message.member != "Activated":
            return False
        self._on_activated(*message.body)
        return False

    def _create_response_future(self, request_path: str) -> asyncio.Future[tuple[int, dict[str, Any]]]:
        response_future: asyncio.Future[tuple[int, dict[str, Any]]] = self._loop.create_future()

        def handler(message: Any) -> bool:
            if message.path != request_path:
                return False
            if message.interface != REQUEST_INTERFACE or message.member != "Response":
                return False
            if not response_future.done():
                response_future.set_result((int(message.body[0]), dict(message.body[1])))
            return False

        self._bus.add_message_handler(handler)
        return response_future

    def _on_activated(
        self,
        session_handle: str,
        shortcut_id: str,
        _timestamp: int,
        _options: dict[str, Any],
    ) -> None:
        if session_handle != self._session_handle:
            return
        if shortcut_id != READ_ACTIVE_SOURCE_SHORTCUT_ID:
            return
        if self._callback is not None:
            self._callback()

    async def _shutdown_bus(self) -> None:
        if self._bus is None:
            return
        self._bus.disconnect()


def _make_token(prefix: str) -> str:
    return f"textreader_{prefix}_{uuid.uuid4().hex}"


def _request_path_for_bus(unique_name: str, token: str) -> str:
    sender = unique_name[1:].replace(".", "_")
    return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"


def _registration_from_response(results: dict[str, Any]) -> GlobalShortcutRegistration:
    shortcuts = results.get("shortcuts", [])
    if not shortcuts:
        return GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.ERROR,
            message="Portal did not return any bound shortcuts.",
        )

    shortcut_id, shortcut_properties = shortcuts[0]
    trigger_description = _read_trigger_description(shortcut_properties)
    if shortcut_id != READ_ACTIVE_SOURCE_SHORTCUT_ID:
        return GlobalShortcutRegistration(
            status=GlobalShortcutPortalStatus.ERROR,
            message="Portal returned an unexpected shortcut identifier.",
        )
    return GlobalShortcutRegistration(
        status=GlobalShortcutPortalStatus.READY,
        message="Global shortcut portal registration succeeded.",
        trigger_description=trigger_description,
    )


def _read_trigger_description(properties: dict[str, Any]) -> str | None:
    description = properties.get("trigger_description")
    if description is None:
        return None
    if hasattr(description, "value"):
        return str(description.value)
    return str(description)
