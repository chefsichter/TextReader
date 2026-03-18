"""Application orchestration for the current TextReader slice."""

from __future__ import annotations

from dataclasses import dataclass

from text_reader_app.audio import AudioPlaybackController
from text_reader_app.app_runtime_paths import AppRuntimePaths
from text_reader_app.capture import CaptureMode, TextCaptureService
from text_reader_app.domain.models import HistoryEntry, HistoryEntryStatus
from text_reader_app.history import HistoryRepository
from text_reader_app.settings import SettingsRepository
from text_reader_app.tts import QwenSpeechSynthesizer, QwenSynthesisResult


@dataclass(slots=True)
class ApplicationController:
    """Wire repositories and runtime services for the current app slice."""

    settings_repository: SettingsRepository
    history_repository: HistoryRepository
    text_capture_service: TextCaptureService
    audio_playback_controller: AudioPlaybackController
    qwen_speech_synthesizer: QwenSpeechSynthesizer
    runtime_paths: AppRuntimePaths

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

    def prepare(self) -> QwenSynthesisResult:
        """Expose the lazy synthesizer preparation for future callers."""

        return self.qwen_speech_synthesizer.prepare()

    def synthesize(self, text: str) -> QwenSynthesisResult:
        """Attempt synthesis and load the resulting audio if one exists."""

        result = self.qwen_speech_synthesizer.synthesize(text)
        if result.audio_path:
            self.audio_playback_controller.load_audio(result.audio_path)
        return result

    def capture_and_store(self, mode: CaptureMode | str) -> HistoryEntry:
        """Capture text for the requested mode and persist it immediately."""

        captured_text = self.text_capture_service.capture(mode)
        history_entry = HistoryEntry.new(
            source_type=captured_text.source_type,
            text=captured_text.text,
        )
        return self.history_repository.create(history_entry)

    def process_capture(self, mode: CaptureMode | str) -> tuple[HistoryEntry, QwenSynthesisResult]:
        """Capture, persist, attempt synthesis, and persist the new state."""

        history_entry = self.capture_and_store(mode)
        result = self.synthesize(history_entry.text)
        self._update_history_from_synthesis(history_entry, result)
        return history_entry, result

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
        qwen_speech_synthesizer=QwenSpeechSynthesizer(),
        runtime_paths=runtime_paths,
    )
    _ensure_default_settings(controller)
    return controller


def _ensure_default_settings(controller: ApplicationController) -> None:
    defaults = {
        "capture_mode": CaptureMode.CLIPBOARD.value,
        "jump_seconds": "5",
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
