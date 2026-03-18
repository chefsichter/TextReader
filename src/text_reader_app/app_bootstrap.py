"""Application bootstrap for the TextReader tray app."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from text_reader_app.application_controller import build_application_controller
from text_reader_app.app_runtime_paths import AppRuntimePaths, build_runtime_paths


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RuntimeContext:
    """Service container passed into the GUI shell."""

    settings_repository: Any
    history_repository: Any
    text_capture_service: Any
    audio_playback_controller: Any
    qwen_speech_synthesizer: Any
    application_controller: Any
    hotkey_service: Any | None
    app_runtime_paths: AppRuntimePaths
    capture_mode: str
    jump_seconds: int
    hotkey_trigger: str


def configure_logging() -> None:
    """Configure a minimal console logger for the app."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_application(argv: list[str] | None = None) -> QApplication:
    """Create the Qt application instance."""

    qt_argv = argv if argv is not None else sys.argv
    app = QApplication(qt_argv)
    app.setApplicationName("TextReader")
    app.setQuitOnLastWindowClosed(False)
    return app


def build_runtime_context() -> RuntimeContext:
    """Create runtime services and wrap them in a GUI-facing context."""

    app = QApplication.instance()
    if app is None:
        msg = "QApplication must exist before building the runtime context."
        raise RuntimeError(msg)

    runtime_paths = build_runtime_paths(app.applicationName())
    controller = build_application_controller(runtime_paths)
    hotkey_service = _build_hotkey_service(
        controller=controller,
        application_name=app.applicationName(),
    )
    return RuntimeContext(
        settings_repository=controller.settings_repository,
        history_repository=controller.history_repository,
        text_capture_service=controller.text_capture_service,
        audio_playback_controller=controller.audio_playback_controller,
        qwen_speech_synthesizer=controller.qwen_speech_synthesizer,
        application_controller=controller,
        hotkey_service=controller.attach_hotkey_service(hotkey_service),
        app_runtime_paths=runtime_paths,
        capture_mode=controller.capture_mode(),
        jump_seconds=controller.jump_seconds(),
        hotkey_trigger=controller.hotkey_trigger(),
    )


def create_ui(runtime_context: RuntimeContext) -> list[object]:
    """Create UI objects if the GUI package is already present."""

    try:
        from text_reader_app.gui import create_gui_shell
    except ImportError:
        LOGGER.info("GUI shell not available yet; bootstrap scaffold is ready.")
        return []

    ui_objects = create_gui_shell(runtime_context)
    if ui_objects is None:
        return []
    if isinstance(ui_objects, list):
        return ui_objects
    return [ui_objects]


def run(argv: list[str] | None = None) -> int:
    """Boot the application and start the Qt event loop when UI exists."""

    configure_logging()
    app = build_application(argv)

    # QAudioOutput/QMediaPlayer require a running event loop on Linux/PipeWire.
    # Defer all service initialization until after app.exec() has started.
    _held_refs: list[object] = []

    def _deferred_init() -> None:
        runtime_context = build_runtime_context()
        ui_objects = create_ui(runtime_context)
        if not ui_objects:
            LOGGER.info("Exiting because no GUI shell is registered yet.")
            app.quit()
            return
        _held_refs.extend(ui_objects)

    QTimer.singleShot(0, _deferred_init)
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    """Console script entry point."""

    return run(argv)


def _build_hotkey_service(controller: Any, application_name: str) -> Any | None:
    callback = controller.handle_hotkey_activation
    trigger = controller.hotkey_trigger()

    portal_service = _build_backend_service(
        class_path=(
            "text_reader_app.hotkeys",
            ("GlobalShortcutPortalService",),
        ),
        application_name=application_name,
        trigger=trigger,
        callback=callback,
    )
    if _registration_is_ready(portal_service):
        LOGGER.info("Using portal hotkey backend.")
        return portal_service

    if _should_try_gnome_shell_fallback(portal_service):
        _log_backend_unavailable("Portal hotkey backend", portal_service)
        gnome_service = _build_backend_service(
            class_path=(
                "text_reader_app.hotkeys.gnome_shell_hotkey",
                (
                    "GnomeShellHotkeyService",
                    "GnomeShellGlobalHotkeyService",
                    "GnomeShellAcceleratorService",
                ),
            ),
            application_name=application_name,
            trigger=trigger,
            callback=callback,
        )
        if _registration_is_ready(gnome_service):
            LOGGER.info("Using GNOME Shell hotkey fallback backend.")
            return gnome_service
        _log_backend_unavailable("GNOME Shell fallback", gnome_service)
        return gnome_service or portal_service

    _log_backend_unavailable("Portal hotkey backend", portal_service)
    return portal_service


def _build_backend_service(
    *,
    class_path: tuple[str, tuple[str, ...]],
    application_name: str,
    trigger: str,
    callback: Any,
) -> Any | None:
    hotkey_class = _import_backend_class(*class_path)
    if hotkey_class is None:
        return None

    hotkey_service = _instantiate_hotkey_service(
        hotkey_class=hotkey_class,
        application_name=application_name,
        trigger=trigger,
        callback=callback,
    )
    _start_hotkey_service(hotkey_service)
    return hotkey_service


def _import_backend_class(module_name: str, class_names: tuple[str, ...]) -> type | None:
    try:
        module = __import__(module_name, fromlist=list(class_names))
    except ImportError:
        return None

    for class_name in class_names:
        hotkey_class = getattr(module, class_name, None)
        if hotkey_class is not None:
            return hotkey_class
    return None


def _instantiate_hotkey_service(
    hotkey_class: type,
    application_name: str,
    trigger: str,
    callback: Any,
) -> Any:
    try:
        return hotkey_class(
            application_name=application_name,
            preferred_trigger=trigger,
            on_activated=callback,
        )
    except TypeError:
        return hotkey_class(
            preferred_trigger=trigger,
            on_activated=callback,
        )


def _start_hotkey_service(hotkey_service: Any | None) -> None:
    if hotkey_service is None:
        return

    for method_name in ("start", "register"):
        method = getattr(hotkey_service, method_name, None)
        if callable(method):
            method()
            return


def _should_try_gnome_shell_fallback(portal_service: Any | None) -> bool:
    return _is_gnome_wayland_session() or _registration_is_unavailable(portal_service)


def _is_gnome_wayland_session() -> bool:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").strip().lower()
    desktop_session = os.environ.get("DESKTOP_SESSION", "").strip().lower()
    is_wayland = session_type == "wayland"
    desktop_tokens = {token for token in current_desktop.split(":") if token}
    desktop_tokens.add(desktop_session)
    return is_wayland and any(token in {"gnome", "zorin"} for token in desktop_tokens)


def _registration_is_ready(hotkey_service: Any | None) -> bool:
    registration = _service_registration(hotkey_service)
    if registration is None:
        return False
    ok = getattr(registration, "ok", None)
    if isinstance(ok, bool):
        return ok
    return str(getattr(registration, "status", "")).lower() == "ready"


def _registration_is_unavailable(hotkey_service: Any | None) -> bool:
    registration = _service_registration(hotkey_service)
    if registration is None:
        return True
    return str(getattr(registration, "status", "")).lower() == "not_available"


def _service_registration(hotkey_service: Any | None) -> Any | None:
    if hotkey_service is None:
        return None
    return getattr(hotkey_service, "registration", None)


def _log_backend_unavailable(label: str, hotkey_service: Any | None) -> None:
    registration = _service_registration(hotkey_service)
    if registration is None:
        LOGGER.info("%s is not available.", label)
        return

    message = getattr(registration, "message", None) or "No status message was provided."
    LOGGER.info("%s is unavailable: %s", label, message)
