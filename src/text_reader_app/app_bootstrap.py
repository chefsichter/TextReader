"""Application bootstrap for the TextReader tray app."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication

from text_reader_app.audio import AudioPlaybackController
from text_reader_app.capture import TextCaptureService
from text_reader_app.history import HistoryRepository
from text_reader_app.settings import SettingsRepository
from text_reader_app.tts import QwenSpeechSynthesizer


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RuntimeContext:
    """Placeholder service container for the first scaffold."""

    settings_repository: Any | None = None
    history_repository: Any | None = None
    text_capture_service: Any | None = None
    audio_playback_controller: Any | None = None
    qwen_speech_synthesizer: Any | None = None
    app_data_directory: Path | None = None


def configure_logging() -> None:
    """Configure a minimal console logger for the app."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_runtime_context() -> RuntimeContext:
    """Return the placeholder service wiring for the initial scaffold."""
    app = QApplication.instance()
    if app is None:
        msg = "QApplication must exist before building the runtime context."
        raise RuntimeError(msg)

    app_data_directory = Path(app.applicationName()).expanduser()
    data_root = Path.home() / ".local" / "share" / app_data_directory
    database_path = data_root / "text_reader.sqlite3"

    settings_repository = SettingsRepository(database_path)
    history_repository = HistoryRepository(database_path)
    text_capture_service = TextCaptureService()
    audio_playback_controller = AudioPlaybackController()
    qwen_speech_synthesizer = QwenSpeechSynthesizer()
    settings_repository.initialize()
    history_repository.initialize()

    return RuntimeContext(
        settings_repository=settings_repository,
        history_repository=history_repository,
        text_capture_service=text_capture_service,
        audio_playback_controller=audio_playback_controller,
        qwen_speech_synthesizer=qwen_speech_synthesizer,
        app_data_directory=data_root,
    )


def build_application(argv: list[str] | None = None) -> QApplication:
    """Create the Qt application instance."""
    qt_argv = argv if argv is not None else sys.argv
    app = QApplication(qt_argv)
    app.setApplicationName("TextReader")
    app.setQuitOnLastWindowClosed(False)
    return app


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
    runtime_context = build_runtime_context()
    ui_objects = create_ui(runtime_context)

    if not ui_objects:
        LOGGER.info("Exiting because no GUI shell is registered yet.")
        return 0

    return app.exec()


def main(argv: list[str] | None = None) -> int:
    """Console script entry point."""
    return run(argv)
