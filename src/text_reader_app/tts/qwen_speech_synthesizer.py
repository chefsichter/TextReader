"""Qwen synthesizer shell with lazy dependency handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .qwen_runtime_config import (
    QwenRuntimeConfig,
    build_default_qwen_runtime_config,
)


class QwenSynthesizerStatus(StrEnum):
    """Stable status values for the synthesizer shell."""

    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class QwenSynthesisResult:
    """Return object for prepare/synthesize shell calls."""

    status: QwenSynthesizerStatus
    message: str
    audio_path: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether the operation succeeded."""

        return self.status == QwenSynthesizerStatus.READY


class QwenSpeechSynthesizer:
    """Lazy shell around qwen_tts that never crashes the app on import."""

    def __init__(self, runtime_config: QwenRuntimeConfig | None = None) -> None:
        self._runtime_config = runtime_config or build_default_qwen_runtime_config()
        self._backend: Any | None = None
        self._prepare_result: QwenSynthesisResult | None = None

    @property
    def runtime_config(self) -> QwenRuntimeConfig:
        """Return the configured runtime defaults."""

        return self._runtime_config

    def prepare(self) -> QwenSynthesisResult:
        """Attempt to import and initialize the Qwen backend lazily."""

        if self._prepare_result is not None:
            return self._prepare_result

        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError:
            self._prepare_result = QwenSynthesisResult(
                status=QwenSynthesizerStatus.NOT_CONFIGURED,
                message="qwen_tts is not installed in the active environment.",
            )
            return self._prepare_result

        try:
            self._backend = Qwen3TTSModel.from_pretrained(
                self._runtime_config.model_id,
            )
        except Exception as exc:
            self._prepare_result = QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message=f"Qwen backend could not be prepared: {exc}",
            )
            return self._prepare_result

        self._prepare_result = QwenSynthesisResult(
            status=QwenSynthesizerStatus.READY,
            message="Qwen backend prepared successfully.",
        )
        return self._prepare_result

    def synthesize(self, text: str) -> QwenSynthesisResult:
        """Return a stable placeholder result until file output is added."""

        if not text.strip():
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message="Cannot synthesize empty text.",
            )

        prepare_result = self.prepare()
        if not prepare_result.ok:
            return prepare_result

        return QwenSynthesisResult(
            status=QwenSynthesizerStatus.NOT_CONFIGURED,
            message="Qwen shell is prepared, but audio file synthesis is not wired yet.",
        )
