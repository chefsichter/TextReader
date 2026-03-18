"""GUI shell exports for the TextReader tray application."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QApplication

from text_reader_app.capture import CaptureMode, TextCaptureError
from text_reader_app.domain.models import HistoryEntry, HistoryEntryStatus

from .player_window import PlayerWindow
from .tray_controller import TrayActionCallbacks, TrayController

__all__ = [
    "PlayerWindow",
    "TrayActionCallbacks",
    "TrayController",
    "create_gui_shell",
]


def create_gui_shell(runtime_context: Any) -> list[object]:
    """Build the first tray-first GUI shell for the application."""

    app = QApplication.instance()
    if app is None:
        msg = "QApplication must exist before creating the GUI shell."
        raise RuntimeError(msg)

    player_window = PlayerWindow()
    callbacks = _build_tray_callbacks(runtime_context, player_window)
    tray_controller = TrayController(
        app=app,
        player_window=player_window,
        callbacks=callbacks,
    )
    tray_controller.show()
    return [player_window, tray_controller, runtime_context]


def _build_tray_callbacks(
    runtime_context: Any,
    player_window: PlayerWindow,
) -> TrayActionCallbacks:
    return TrayActionCallbacks(
        on_read_selection=lambda: _capture_and_present(
            runtime_context,
            player_window,
            CaptureMode.SELECTION,
        ),
        on_read_clipboard=lambda: _capture_and_present(
            runtime_context,
            player_window,
            CaptureMode.CLIPBOARD,
        ),
    )


def _capture_and_present(
    runtime_context: Any,
    player_window: PlayerWindow,
    mode: CaptureMode,
) -> None:
    try:
        captured_text = runtime_context.text_capture_service.capture(mode)
        history_entry = HistoryEntry.new(
            source_type=captured_text.source_type,
            text=captured_text.text,
        )
        stored_entry = runtime_context.history_repository.create(history_entry)
    except TextCaptureError as exc:
        player_window.set_status_text("error")
        player_window.set_preview_text(str(exc))
        player_window.show()
        return

    synthesis_result = runtime_context.qwen_speech_synthesizer.synthesize(
        captured_text.text,
    )
    stored_entry.status = _map_synthesis_status_to_history(synthesis_result.status)
    stored_entry.error_message = None if synthesis_result.ok else synthesis_result.message
    runtime_context.history_repository.update(stored_entry)

    player_window.set_status_text(synthesis_result.status)
    player_window.set_preview_text(captured_text.text)
    player_window.show()


def _map_synthesis_status_to_history(status: Any) -> HistoryEntryStatus:
    if str(status) == "ready":
        return HistoryEntryStatus.READY
    if str(status) == "error":
        return HistoryEntryStatus.FAILED
    return HistoryEntryStatus.CAPTURED
