"""GUI shell exports for the TextReader tray application."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QApplication

from text_reader_app.capture import CaptureMode, TextCaptureError

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
        initial_capture_mode=runtime_context.capture_mode,
    )
    _configure_player_window(player_window, runtime_context)
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
        on_capture_mode_changed=lambda mode: _persist_capture_mode(runtime_context, mode),
    )


def _capture_and_present(
    runtime_context: Any,
    player_window: PlayerWindow,
    mode: CaptureMode,
) -> None:
    try:
        stored_entry, synthesis_result = runtime_context.application_controller.process_capture(
            mode,
        )
    except TextCaptureError as exc:
        player_window.set_status_text("error")
        player_window.set_preview_text(str(exc))
        player_window.show()
        return

    _update_player_window_for_capture(runtime_context, player_window, stored_entry)
    player_window.show()


def _configure_player_window(player_window: PlayerWindow, runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    player_window.set_jump_labels(runtime_context.jump_seconds)
    player_window.set_transport_enabled(audio_controller.has_loaded_audio())
    player_window.set_slider_enabled(audio_controller.can_seek())
    player_window.connect_play_pause(lambda: _toggle_playback(runtime_context))
    player_window.connect_stop(audio_controller.stop)
    player_window.connect_jump_backward(
        lambda: _jump_playback(runtime_context, -runtime_context.jump_seconds),
    )
    player_window.connect_jump_forward(
        lambda: _jump_playback(runtime_context, runtime_context.jump_seconds),
    )
    player_window.connect_seek_requested(audio_controller.seek_to_ms)
    audio_controller.player.positionChanged.connect(player_window.set_position_ms)
    audio_controller.player.durationChanged.connect(player_window.set_duration_ms)


def _toggle_playback(runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    if audio_controller.is_playing():
        audio_controller.pause()
        return
    audio_controller.play()


def _jump_playback(runtime_context: Any, jump_seconds: int) -> None:
    runtime_context.audio_playback_controller.jump_by_ms(jump_seconds * 1000)


def _persist_capture_mode(runtime_context: Any, mode: str) -> None:
    runtime_context.capture_mode = runtime_context.application_controller.set_capture_mode(
        mode,
    )


def _update_player_window_for_capture(
    runtime_context: Any,
    player_window: PlayerWindow,
    history_entry: Any,
) -> None:
    audio_controller = runtime_context.audio_playback_controller
    status_text = history_entry.error_message or str(history_entry.status)
    player_window.set_status_text(status_text)
    player_window.set_preview_text(history_entry.text)
    player_window.set_transport_enabled(audio_controller.has_loaded_audio())
    player_window.set_slider_enabled(audio_controller.can_seek())
