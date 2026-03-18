"""GUI shell exports for the TextReader tray application."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from text_reader_app.capture import CaptureMode, TextCaptureError
from text_reader_app.domain.models import AppPreferences, HistoryEntry, HistoryEntryStatus

from .player_window import PlayerWindow
from .preferences_options import LANGUAGE_OPTIONS, READER_OPTIONS
from .settings_window import SettingsFormState, SettingsWindow, SettingsWindowCallbacks
from .synthesis_worker import SynthesisWorker
from .tray_controller import TrayActionCallbacks, TrayController

__all__ = [
    "PlayerWindow",
    "SettingsWindow",
    "TrayActionCallbacks",
    "TrayController",
    "create_gui_shell",
]


def create_gui_shell(runtime_context: Any) -> list[object]:
    """Build the tray UI, player window, settings window, and local bridges."""

    app = QApplication.instance()
    if app is None:
        msg = "QApplication must exist before creating the GUI shell."
        raise RuntimeError(msg)

    player_window = PlayerWindow()
    settings_window = SettingsWindow(
        callbacks=_build_settings_callbacks(runtime_context, player_window),
        initial_state=_settings_form_state(runtime_context.application_controller.preferences()),
    )
    tray_controller = TrayController(
        app=app,
        player_window=player_window,
        initial_capture_mode=runtime_context.capture_mode,
        initial_hotkey_trigger=runtime_context.hotkey_trigger,
        initial_reader=runtime_context.voice,
        initial_language=runtime_context.language,
        initial_synthesis_mode=runtime_context.synthesis_mode,
        reader_options=READER_OPTIONS,
        language_options=LANGUAGE_OPTIONS,
    )
    tray_controller.set_callbacks(
        _build_tray_callbacks(
            runtime_context,
            player_window,
            settings_window,
            tray_controller,
        ),
    )
    _wire_tray_hotkey_change(
        tray_controller,
        runtime_context,
        settings_window,
        player_window,
    )
    _configure_player_window(player_window, runtime_context)
    player_window.set_theme(runtime_context.theme)
    player_window.connect_theme_toggle(
        lambda: _toggle_theme(runtime_context, player_window),
    )
    _restore_recent_history(player_window, runtime_context)
    _wire_local_commands(runtime_context, player_window, settings_window)
    tray_controller.show()
    player_window.show()
    return [player_window, settings_window, tray_controller, runtime_context]


def _build_tray_callbacks(
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
    tray_controller: TrayController,
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
        on_reader_changed=lambda reader: _update_reader_from_tray(
            runtime_context,
            player_window,
            settings_window,
            tray_controller,
            reader=reader,
        ),
        on_language_changed=lambda language: _update_language_from_tray(
            runtime_context,
            player_window,
            settings_window,
            tray_controller,
            language=language,
        ),
        on_synthesis_mode_changed=lambda synthesis_mode: _update_synthesis_mode_from_tray(
            runtime_context,
            player_window,
            settings_window,
            tray_controller,
            synthesis_mode=synthesis_mode,
        ),
        on_open_settings=settings_window.show,
        on_change_hotkey=lambda: _change_hotkey_from_tray(
            runtime_context,
            settings_window,
            player_window,
        ),
    )


def _build_settings_callbacks(
    runtime_context: Any,
    player_window: PlayerWindow,
) -> SettingsWindowCallbacks:
    return SettingsWindowCallbacks(
        on_load_requested=lambda: _settings_form_state(
            runtime_context.application_controller.preferences(),
        ),
        on_save_requested=lambda form_state: _save_settings(
            runtime_context,
            player_window,
            form_state,
        ),
    )


def _configure_player_window(player_window: PlayerWindow, runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    player_window.set_jump_labels(runtime_context.jump_seconds)
    player_window.set_transport_enabled(audio_controller.has_loaded_audio())
    player_window.set_slider_enabled(audio_controller.can_seek())
    player_window.set_playback_state(audio_controller.playback_state_name())
    player_window.connect_play_pause(lambda: _toggle_playback(runtime_context))
    player_window.connect_previous_history(
        lambda: _load_history_neighbor(runtime_context, player_window, "previous"),
    )
    player_window.connect_next_history(
        lambda: _load_history_neighbor(runtime_context, player_window, "next"),
    )
    player_window.connect_stop(audio_controller.stop)
    player_window.connect_jump_backward(
        lambda: _jump_playback(runtime_context, -runtime_context.jump_seconds),
    )
    player_window.connect_jump_forward(
        lambda: _jump_playback(runtime_context, runtime_context.jump_seconds),
    )
    player_window.connect_seek_requested(
        lambda position_ms: _seek_playback(runtime_context, position_ms),
    )
    audio_controller.player.positionChanged.connect(
        lambda position_ms: _sync_position(runtime_context, player_window, position_ms),
    )
    audio_controller.player.durationChanged.connect(
        lambda duration_ms: _sync_duration(runtime_context, player_window, duration_ms),
    )
    audio_controller.player.playbackStateChanged.connect(
        lambda _state: _sync_playback_state(player_window, runtime_context),
    )
    audio_controller.player.mediaStatusChanged.connect(
        lambda _status: _sync_media_availability(player_window, runtime_context),
    )


def _capture_and_present(
    runtime_context: Any,
    player_window: PlayerWindow,
    mode: CaptureMode,
) -> None:
    try:
        stored_entry = runtime_context.application_controller.capture_and_store(mode)
    except TextCaptureError as exc:
        player_window.set_status_text("error")
        player_window.set_preview_text(str(exc))
        player_window.show()
        return

    _present_history_entry(runtime_context, player_window, stored_entry)
    player_window.set_status_text("synthesizing")
    _start_synthesis_worker(runtime_context, player_window, stored_entry)
    player_window.show()


def _persist_capture_mode(runtime_context: Any, mode: str) -> None:
    runtime_context.capture_mode = runtime_context.application_controller.set_capture_mode(mode)


def _toggle_theme(runtime_context: Any, player_window: PlayerWindow) -> None:
    new_theme = "light" if runtime_context.theme == "dark" else "dark"
    runtime_context.theme = runtime_context.application_controller.set_theme(new_theme)
    player_window.set_theme(new_theme)
    from text_reader_app.gui.style_loader import apply_stylesheet
    apply_stylesheet(new_theme)


def _save_settings(
    runtime_context: Any,
    player_window: PlayerWindow,
    form_state: SettingsFormState,
) -> AppPreferences:
    preferences = runtime_context.application_controller.save_preferences(
        capture_mode=form_state.capture_mode,
        hotkey_trigger=form_state.hotkey_trigger,
        jump_seconds=form_state.jump_seconds,
        voice=form_state.voice,
        language=form_state.language,
        synthesis_mode=form_state.synthesis_mode,
        theme=form_state.theme,
    )
    runtime_context.capture_mode = preferences.capture_mode
    runtime_context.jump_seconds = preferences.jump_seconds
    runtime_context.hotkey_trigger = preferences.hotkey_trigger
    runtime_context.voice = preferences.voice
    runtime_context.language = preferences.language
    runtime_context.synthesis_mode = preferences.synthesis_mode
    runtime_context.theme = preferences.theme
    player_window.set_jump_labels(preferences.jump_seconds)
    player_window.set_theme(preferences.theme)
    player_window.set_status_text("settings saved")
    from text_reader_app.gui.style_loader import apply_stylesheet
    apply_stylesheet(preferences.theme)
    return preferences


def _change_hotkey_from_tray(
    runtime_context: Any,
    settings_window: SettingsWindow,
    player_window: PlayerWindow,
) -> None:
    settings_window.change_hotkey()
    _save_settings(runtime_context, player_window, settings_window.state())


def _wire_tray_hotkey_change(
    tray_controller: TrayController,
    runtime_context: Any,
    settings_window: SettingsWindow,
    player_window: PlayerWindow,
) -> None:
    original_save_callback = settings_window.save_callback()

    def save_and_refresh(form_state: SettingsFormState) -> None:
        preferences: AppPreferences | None = None
        if original_save_callback is not None:
            preferences = original_save_callback(form_state)
        if preferences is None:
            return
        _sync_settings_views(tray_controller, settings_window, preferences)

    settings_window.set_save_callback(save_and_refresh)
    _sync_settings_views(
        tray_controller,
        settings_window,
        runtime_context.application_controller.preferences(),
    )


def _update_reader_from_tray(
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
    tray_controller: TrayController,
    reader: str,
) -> None:
    settings_window.set_reader(reader)
    preferences = _save_settings(runtime_context, player_window, settings_window.state())
    _sync_settings_views(tray_controller, settings_window, preferences)


def _update_language_from_tray(
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
    tray_controller: TrayController,
    language: str,
) -> None:
    settings_window.set_language(language)
    preferences = _save_settings(runtime_context, player_window, settings_window.state())
    _sync_settings_views(tray_controller, settings_window, preferences)


def _update_synthesis_mode_from_tray(
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
    tray_controller: TrayController,
    synthesis_mode: str,
) -> None:
    settings_window.set_synthesis_mode(synthesis_mode)
    preferences = _save_settings(runtime_context, player_window, settings_window.state())
    _sync_settings_views(tray_controller, settings_window, preferences)


def _sync_settings_views(
    tray_controller: TrayController,
    settings_window: SettingsWindow,
    preferences: AppPreferences,
) -> None:
    settings_window.set_state(_settings_form_state(preferences))
    tray_controller.set_hotkey_trigger(preferences.hotkey_trigger)
    tray_controller.set_reader(preferences.voice)
    tray_controller.set_language(preferences.language)
    tray_controller.set_synthesis_mode(preferences.synthesis_mode)


def _toggle_playback(runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    if audio_controller.is_playing():
        audio_controller.pause()
        return
    audio_controller.play()


def _jump_playback(runtime_context: Any, jump_seconds: int) -> None:
    runtime_context.audio_playback_controller.jump_by_ms(jump_seconds * 1000)


def _seek_playback(runtime_context: Any, position_ms: int) -> None:
    runtime_context.audio_playback_controller.seek_to_ms(position_ms)
    runtime_context.application_controller.remember_playback_position(position_ms)


def _sync_duration(runtime_context: Any, player_window: PlayerWindow, duration_ms: int) -> None:
    player_window.set_duration_ms(duration_ms)
    current_entry = runtime_context.application_controller.current_history_entry()
    if current_entry is None or current_entry.id is None:
        return
    runtime_context.history_repository.update_playback_state(
        current_entry.id,
        duration_ms=duration_ms,
    )


def _sync_position(runtime_context: Any, player_window: PlayerWindow, position_ms: int) -> None:
    player_window.set_position_ms(position_ms)


def _load_history_neighbor(
    runtime_context: Any,
    player_window: PlayerWindow,
    direction: str,
) -> None:
    history_entry = runtime_context.application_controller.load_adjacent_history_entry(
        direction,
        autoplay=False,
    )
    if history_entry is None:
        return
    _present_history_entry(runtime_context, player_window, history_entry)


def _present_history_entry(
    runtime_context: Any,
    player_window: PlayerWindow,
    history_entry: HistoryEntry,
) -> None:
    audio_controller = runtime_context.audio_playback_controller
    status_text = history_entry.error_message or str(history_entry.status)
    player_window.set_status_text(status_text)
    player_window.set_preview_text(history_entry.text)
    player_window.set_entry_source_text(history_entry.source_type)
    player_window.set_entry_context_text(_history_context_text(history_entry))
    player_window.set_transport_enabled(audio_controller.has_loaded_audio())
    player_window.set_slider_enabled(audio_controller.can_seek())
    player_window.set_playback_state(audio_controller.playback_state_name())
    _sync_navigation(player_window, runtime_context)


def _restore_recent_history(player_window: PlayerWindow, runtime_context: Any) -> None:
    latest_entry = runtime_context.history_repository.latest()
    if latest_entry is None or latest_entry.id is None:
        _sync_navigation(player_window, runtime_context)
        return

    runtime_context.application_controller.current_history_entry_id = latest_entry.id
    runtime_context.application_controller.load_history_entry(latest_entry.id, autoplay=False)
    _present_history_entry(runtime_context, player_window, latest_entry)
    _sync_media_availability(player_window, runtime_context)


def _start_synthesis_worker(
    runtime_context: Any,
    player_window: PlayerWindow,
    history_entry: HistoryEntry,
) -> None:
    worker = SynthesisWorker(runtime_context.application_controller, history_entry)
    runtime_context.background_jobs.append(worker)
    worker.signals.finished.connect(
        lambda entry, result: _finish_synthesis(
            runtime_context,
            player_window,
            entry,
            result,
            worker,
        ),
    )
    worker.signals.failed.connect(
        lambda entry, message: _handle_synthesis_failure(
            runtime_context,
            player_window,
            entry,
            message,
            worker,
        ),
    )
    QThreadPool.globalInstance().start(worker)


def _finish_synthesis(
    runtime_context: Any,
    player_window: PlayerWindow,
    history_entry: HistoryEntry,
    result: Any,
    worker: SynthesisWorker,
) -> None:
    updated_entry = runtime_context.application_controller.complete_synthesis(
        history_entry,
        result,
        autoplay=True,
    )
    _discard_background_job(runtime_context, worker)
    _present_history_entry(runtime_context, player_window, updated_entry)
    player_window.set_status_text(result.message if not result.ok else "ready")
    _sync_media_availability(player_window, runtime_context)


def _handle_synthesis_failure(
    runtime_context: Any,
    player_window: PlayerWindow,
    history_entry: HistoryEntry,
    message: str,
    worker: SynthesisWorker,
) -> None:
    _discard_background_job(runtime_context, worker)
    history_entry.error_message = message
    history_entry.status = HistoryEntryStatus.FAILED
    if history_entry.id is not None:
        runtime_context.history_repository.update(history_entry)
    player_window.set_status_text("error")
    player_window.set_preview_text(message)


def _discard_background_job(runtime_context: Any, worker: SynthesisWorker) -> None:
    if worker in runtime_context.background_jobs:
        runtime_context.background_jobs.remove(worker)


def _sync_playback_state(player_window: PlayerWindow, runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    player_window.set_playback_state(audio_controller.playback_state_name())
    runtime_context.application_controller.remember_playback_position(
        audio_controller.position_ms(),
    )


def _sync_media_availability(player_window: PlayerWindow, runtime_context: Any) -> None:
    audio_controller = runtime_context.audio_playback_controller
    player_window.set_transport_enabled(audio_controller.has_loaded_audio())
    player_window.set_slider_enabled(audio_controller.can_seek())
    if not audio_controller.has_loaded_audio():
        player_window.reset_playback_position()
        return
    player_window.set_duration_ms(audio_controller.duration_ms())
    player_window.set_position_ms(audio_controller.position_ms())


def _sync_navigation(player_window: PlayerWindow, runtime_context: Any) -> None:
    navigation = runtime_context.application_controller.history_navigation()
    player_window.set_history_position(
        navigation.current_position,
        navigation.total_entries,
    )
    player_window.set_history_navigation_enabled(
        has_previous=navigation.has_previous,
        has_next=navigation.has_next,
    )


def _wire_local_commands(
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
) -> None:
    server = runtime_context.local_command_server
    if server is None:
        return
    server.command_received.connect(
        lambda command: _handle_ui_local_command(
            command,
            runtime_context,
            player_window,
            settings_window,
        ),
    )


def _handle_ui_local_command(
    command: str,
    runtime_context: Any,
    player_window: PlayerWindow,
    settings_window: SettingsWindow,
) -> None:
    if command == "show-player":
        player_window.show()
        player_window.raise_()
        player_window.activateWindow()
        return
    if command == "show-settings":
        settings_window.show()
        settings_window.raise_()
        settings_window.activateWindow()
        return
    if command == "trigger-active-source":
        _capture_and_present(
            runtime_context,
            player_window,
            CaptureMode(runtime_context.capture_mode),
        )


def _settings_form_state(preferences: AppPreferences) -> SettingsFormState:
    return SettingsFormState(
        capture_mode=preferences.capture_mode,
        hotkey_trigger=preferences.hotkey_trigger,
        jump_seconds=preferences.jump_seconds,
        voice=preferences.voice,
        language=preferences.language,
        synthesis_mode=preferences.synthesis_mode,
        theme=preferences.theme,
    )


def _history_context_text(history_entry: HistoryEntry) -> str:
    parts = [history_entry.created_at.strftime("%Y-%m-%d %H:%M:%S")]
    if history_entry.voice:
        parts.append(f"voice={history_entry.voice}")
    if history_entry.language:
        parts.append(f"language={history_entry.language}")
    return " | ".join(parts)
