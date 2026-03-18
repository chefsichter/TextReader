"""Application orchestration for the current TextReader slice."""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from text_reader_app.audio import AudioPlaybackController
from text_reader_app.app_runtime_paths import AppRuntimePaths
from text_reader_app.capture import CaptureMode, TextCaptureService
from text_reader_app.domain.models import AppPreferences, HistoryEntry, HistoryEntryStatus
from text_reader_app.history import HistoryRepository
from text_reader_app.settings import SettingsRepository
from text_reader_app.tts import (
    QwenSpeechSynthesizer,
    QwenSynthesisResult,
    QwenSynthesizerStatus,
)


@dataclass(slots=True)
class ApplicationController:
    """Wire repositories and runtime services for the current app slice."""

    settings_repository: SettingsRepository
    history_repository: HistoryRepository
    text_capture_service: TextCaptureService
    audio_playback_controller: AudioPlaybackController
    qwen_speech_synthesizer: QwenSpeechSynthesizer
    runtime_paths: AppRuntimePaths
    hotkey_service: object | None = None
    current_history_entry_id: int | None = None

    def capture_mode(self) -> str:
        """Return the persisted active capture mode."""

        value = self.settings_repository.get_value(
            "capture_mode",
            CaptureMode.CLIPBOARD.value,
        )
        try:
            return CaptureMode(value or CaptureMode.CLIPBOARD.value).value
        except ValueError:
            return CaptureMode.CLIPBOARD.value

    def set_capture_mode(self, mode: CaptureMode | str) -> str:
        """Persist the active capture mode and return the normalized value."""

        normalized_mode = CaptureMode(mode).value
        self.settings_repository.set("capture_mode", normalized_mode)
        return normalized_mode

    def jump_seconds(self) -> int:
        """Return the configured playback jump size in seconds."""

        raw_value = self.settings_repository.get_value("jump_seconds", "5")
        try:
            return max(1, int(raw_value or "5"))
        except ValueError:
            return 5

    def set_jump_seconds(self, jump_seconds: int) -> int:
        """Persist and normalize the playback jump size."""

        normalized_value = max(1, int(jump_seconds))
        self.settings_repository.set("jump_seconds", str(normalized_value))
        return normalized_value

    def hotkey_trigger(self) -> str:
        """Return the configured global hotkey trigger string."""

        return self.settings_repository.get_value("hotkey_trigger", "Alt+L") or "Alt+L"

    def set_hotkey_trigger(self, trigger: str) -> str:
        """Persist the configured global hotkey trigger."""

        normalized_trigger = trigger.strip() or "Alt+L"
        self.settings_repository.set("hotkey_trigger", normalized_trigger)
        return normalized_trigger

    def voice(self) -> str:
        """Return the configured speaker id."""

        return (
            self.settings_repository.get_value(
                "voice",
                self.qwen_speech_synthesizer.runtime_config.speaker,
            )
            or self.qwen_speech_synthesizer.runtime_config.speaker
        )

    def language(self) -> str:
        """Return the configured synthesis language."""

        return (
            self.settings_repository.get_value(
                "language",
                self.qwen_speech_synthesizer.runtime_config.language,
            )
            or self.qwen_speech_synthesizer.runtime_config.language
        )

    def preferences(self) -> AppPreferences:
        """Return a normalized snapshot of persisted application settings."""

        return AppPreferences(
            capture_mode=self.capture_mode(),
            hotkey_trigger=self.hotkey_trigger(),
            jump_seconds=self.jump_seconds(),
            voice=self.voice(),
            language=self.language(),
        )

    def save_preferences(
        self,
        *,
        capture_mode: str,
        hotkey_trigger: str,
        jump_seconds: int,
        voice: str,
        language: str,
    ) -> AppPreferences:
        """Persist settings and apply runtime TTS choices immediately."""

        normalized_preferences = AppPreferences(
            capture_mode=self.set_capture_mode(capture_mode),
            hotkey_trigger=self.set_hotkey_trigger(hotkey_trigger),
            jump_seconds=self.set_jump_seconds(jump_seconds),
            voice=voice.strip() or self.voice(),
            language=language.strip() or self.language(),
        )
        self.settings_repository.set("voice", normalized_preferences.voice)
        self.settings_repository.set("language", normalized_preferences.language)
        self.qwen_speech_synthesizer.update_runtime_preferences(
            speaker=normalized_preferences.voice,
            language=normalized_preferences.language,
        )
        return normalized_preferences

    def handle_hotkey_activation(self) -> tuple[HistoryEntry, QwenSynthesisResult]:
        """Run the configured active-source capture flow."""

        return self.process_capture(self.capture_mode())

    def attach_hotkey_service(self, hotkey_service: object | None) -> object | None:
        """Retain the active hotkey service when a backend is available."""

        self.hotkey_service = hotkey_service
        return hotkey_service

    def prepare(self) -> QwenSynthesisResult:
        """Expose the lazy synthesizer preparation for future callers."""

        return self.qwen_speech_synthesizer.prepare()

    def synthesize(self, text: str) -> QwenSynthesisResult:
        """Attempt synthesis and load the resulting audio if one exists."""

        result = self.qwen_speech_synthesizer.synthesize(text)
        if not result.ok or not result.audio_path:
            return result

        return self._load_result_audio(result)

    def capture_and_store(self, mode: CaptureMode | str) -> HistoryEntry:
        """Capture text for the requested mode and persist it immediately."""

        captured_text = self.text_capture_service.capture(mode)
        history_entry = HistoryEntry.new(
            source_type=captured_text.source_type,
            text=captured_text.text,
        )
        created_entry = self.history_repository.create(history_entry)
        self.current_history_entry_id = created_entry.id
        return created_entry

    def process_capture(self, mode: CaptureMode | str) -> tuple[HistoryEntry, QwenSynthesisResult]:
        """Capture, persist, attempt synthesis, and persist the new state."""

        history_entry = self.capture_and_store(mode)
        result = self.synthesize(history_entry.text)
        self.complete_synthesis(history_entry, result)
        return history_entry, result

    def synthesize_text(self, text: str) -> QwenSynthesisResult:
        """Run synthesis without touching playback state from worker threads."""

        return self.qwen_speech_synthesizer.synthesize(text)

    def complete_synthesis(
        self,
        history_entry: HistoryEntry,
        result: QwenSynthesisResult,
        *,
        autoplay: bool = True,
    ) -> HistoryEntry:
        """Persist a synthesis result and load audio on the GUI thread."""

        self._update_history_from_synthesis(history_entry, result)
        updated_entry = history_entry
        if history_entry.id is not None:
            updated_entry = self.history_repository.get(history_entry.id) or history_entry
        if autoplay and result.ok and result.audio_path:
            self._load_result_audio(result)
        return updated_entry

    def _update_history_from_synthesis(
        self,
        history_entry: HistoryEntry,
        result: QwenSynthesisResult,
    ) -> None:
        history_entry.status = _map_synthesis_status(result)
        history_entry.error_message = None if result.ok else result.message
        history_entry.model_id = self.qwen_speech_synthesizer.runtime_config.model_id
        history_entry.language = self.qwen_speech_synthesizer.runtime_config.language
        history_entry.voice = self.qwen_speech_synthesizer.runtime_config.speaker
        history_entry.audio_path = result.audio_path
        self.history_repository.update(history_entry)
        if history_entry.id is not None:
            self.current_history_entry_id = history_entry.id

    def _load_result_audio(self, result: QwenSynthesisResult) -> QwenSynthesisResult:
        try:
            self.audio_playback_controller.load_audio(result.audio_path)
            self.audio_playback_controller.play()
        except Exception as exc:
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message=f"Generated audio could not be loaded: {exc}",
            )
        return result

    def list_recent_history(self, limit: int = 50) -> list[HistoryEntry]:
        """Return recent history entries for the player window."""

        return self.history_repository.list_recent(limit=limit)

    def current_history_entry(self) -> HistoryEntry | None:
        """Return the currently focused history entry, if any."""

        if self.current_history_entry_id is None:
            return self.history_repository.latest()
        return self.history_repository.get(self.current_history_entry_id)

    def load_history_entry(
        self,
        entry_id: int,
        *,
        autoplay: bool = False,
    ) -> HistoryEntry | None:
        """Load one history entry into the player and optionally start playback."""

        history_entry = self.history_repository.get(entry_id)
        if history_entry is None:
            return None
        self.current_history_entry_id = history_entry.id
        self._load_history_audio(history_entry, autoplay=autoplay)
        return history_entry

    def load_adjacent_history_entry(
        self,
        direction: str,
        *,
        autoplay: bool = False,
    ) -> HistoryEntry | None:
        """Load the neighboring history entry in the requested direction."""

        current_entry = self.current_history_entry()
        if current_entry is None or current_entry.id is None:
            return None
        if direction == "previous":
            neighbor = self.history_repository.get_previous(current_entry.id)
        else:
            neighbor = self.history_repository.get_next(current_entry.id)
        if neighbor is None or neighbor.id is None:
            return None
        return self.load_history_entry(neighbor.id, autoplay=autoplay)

    def history_navigation(self) -> object:
        """Return navigation metadata for the current history entry."""

        return self.history_repository.describe_navigation(self.current_history_entry_id)

    def remember_playback_position(self, position_ms: int) -> None:
        """Persist the playback cursor for the focused entry."""

        current_entry = self.current_history_entry()
        if current_entry is None or current_entry.id is None:
            return
        self.history_repository.update_last_position(current_entry.id, position_ms)

    def _load_history_audio(self, history_entry: HistoryEntry, *, autoplay: bool) -> None:
        audio_path = history_entry.audio_path
        if not audio_path:
            self.audio_playback_controller.stop()
            return
        self.audio_playback_controller.load_audio(audio_path)
        if history_entry.last_position_ms:
            self.audio_playback_controller.seek_to_ms(history_entry.last_position_ms)
        if autoplay:
            self.audio_playback_controller.play()


def build_application_controller(runtime_paths: AppRuntimePaths) -> ApplicationController:
    """Create and initialize the runtime services for the current app slice."""

    settings_repository = SettingsRepository(runtime_paths.database_path)
    history_repository = HistoryRepository(runtime_paths.database_path)
    settings_repository.initialize()
    history_repository.initialize()
    controller = ApplicationController(
        settings_repository=settings_repository,
        history_repository=history_repository,
        text_capture_service=TextCaptureService(),
        audio_playback_controller=AudioPlaybackController(),
        qwen_speech_synthesizer=_build_qwen_speech_synthesizer(runtime_paths),
        runtime_paths=runtime_paths,
    )
    _ensure_default_settings(controller)
    controller.qwen_speech_synthesizer.update_runtime_preferences(
        speaker=controller.voice(),
        language=controller.language(),
    )
    return controller


def _build_qwen_speech_synthesizer(
    runtime_paths: AppRuntimePaths,
) -> QwenSpeechSynthesizer:
    constructor = QwenSpeechSynthesizer
    parameters = inspect.signature(constructor).parameters
    if "output_directory" in parameters:
        return constructor(output_directory=runtime_paths.audio_cache_directory)
    if "audio_cache_directory" in parameters:
        return constructor(audio_cache_directory=runtime_paths.audio_cache_directory)

    synthesizer = constructor()
    if hasattr(synthesizer, "set_output_directory"):
        synthesizer.set_output_directory(runtime_paths.audio_cache_directory)
    elif hasattr(synthesizer, "set_audio_cache_directory"):
        synthesizer.set_audio_cache_directory(runtime_paths.audio_cache_directory)
    return synthesizer


def _ensure_default_settings(controller: ApplicationController) -> None:
    defaults = {
        "capture_mode": CaptureMode.CLIPBOARD.value,
        "jump_seconds": "5",
        "hotkey_trigger": "Alt+L",
        "voice": controller.qwen_speech_synthesizer.runtime_config.speaker,
        "language": controller.qwen_speech_synthesizer.runtime_config.language,
    }
    for key, value in defaults.items():
        if controller.settings_repository.get_value(key) is None:
            controller.settings_repository.set(key, value)


def _map_synthesis_status(result: QwenSynthesisResult) -> HistoryEntryStatus:
    status_name = str(result.status)
    if status_name == "ready":
        return HistoryEntryStatus.READY
    if status_name == "error":
        return HistoryEntryStatus.FAILED
    return HistoryEntryStatus.CAPTURED
