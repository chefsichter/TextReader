"""Qwen synthesizer shell backed by a persistent TTS subprocess."""

from __future__ import annotations

from array import array
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any
import wave

from .qwen_runtime_config import (
    QwenRuntimeConfig,
    build_default_qwen_runtime_config,
)
from .tts_subprocess import SynthesisCancelledError, TTSModelServer


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
    sample_rate: int | None = None
    speaker: str | None = None
    language: str | None = None
    model_id: str | None = None
    elapsed_ms: int | None = None
    audio_duration_ms: int | None = None

    @property
    def ok(self) -> bool:
        """Return whether the operation succeeded."""
        return self.status == QwenSynthesizerStatus.READY


class QwenSpeechSynthesizer:
    """Shell around a persistent TTS subprocess.  Never imports torch in the main process."""

    def __init__(
        self,
        runtime_config: QwenRuntimeConfig | None = None,
        output_directory: str | Path | None = None,
    ) -> None:
        self._runtime_config = runtime_config or build_default_qwen_runtime_config()
        self._output_directory = _normalize_output_directory(output_directory)
        self._server: TTSModelServer | None = None
        # Only cache non-recoverable failures (NOT_CONFIGURED, import errors).
        self._fatal_result: QwenSynthesisResult | None = None

    @property
    def runtime_config(self) -> QwenRuntimeConfig:
        """Return the configured runtime defaults."""
        return self._runtime_config

    @property
    def output_directory(self) -> Path | None:
        """Return the configured default output directory."""
        return self._output_directory

    def update_runtime_preferences(
        self,
        *,
        speaker: str,
        language: str,
        non_streaming_mode: bool | None = None,
    ) -> None:
        """Apply persisted user choices.

        Speaker, language, and mode are passed per-request so the subprocess
        does not need to be restarted when these change.
        """
        self._runtime_config = replace(
            self._runtime_config,
            speaker=speaker.strip() or self._runtime_config.speaker,
            language=language.strip() or self._runtime_config.language,
            non_streaming_mode=(
                self._runtime_config.non_streaming_mode
                if non_streaming_mode is None
                else bool(non_streaming_mode)
            ),
        )

    def prepare(self) -> QwenSynthesisResult:
        """Ensure the TTS subprocess is running and the model is loaded.

        Blocks until the model is ready.  Safe to call from a worker thread.
        Raises ``SynthesisCancelledError`` if cancel() is called while waiting.
        """
        if self._fatal_result is not None:
            return self._fatal_result

        try:
            import qwen_tts as _qt  # noqa: F401
            import torch as _t  # noqa: F401
        except ImportError:
            self._fatal_result = QwenSynthesisResult(
                status=QwenSynthesizerStatus.NOT_CONFIGURED,
                message="qwen_tts or torch is not installed in the active environment.",
            )
            return self._fatal_result

        if self._server is None:
            self._server = TTSModelServer(self._runtime_config)

        error = self._server.ensure_ready()  # may raise SynthesisCancelledError
        if error:
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message=f"Qwen backend could not be prepared: {error}",
            )
        return QwenSynthesisResult(
            status=QwenSynthesizerStatus.READY,
            message="Qwen backend prepared successfully.",
        )

    def synthesize(
        self,
        text: str,
        output_directory: str | Path | None = None,
        *,
        speaker: str | None = None,
        language: str | None = None,
        non_streaming_mode: bool | None = None,
    ) -> QwenSynthesisResult:
        """Synthesize text into a WAV file.

        Raises ``SynthesisCancelledError`` when synthesis is cancelled mid-run.
        """
        if not text.strip():
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message="Cannot synthesize empty text.",
            )

        prepare_result = self.prepare()  # may raise SynthesisCancelledError
        if not prepare_result.ok:
            return prepare_result

        target_directory = _resolve_target_directory(
            output_directory,
            self._output_directory,
        )
        if target_directory is None:
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message="No output directory was provided for synthesized audio.",
            )

        selected_speaker, selected_language, selected_mode = (
            self._resolve_generation_preferences(
                speaker=speaker,
                language=language,
                non_streaming_mode=non_streaming_mode,
            )
        )

        started_at = perf_counter()
        # May raise SynthesisCancelledError or RuntimeError.
        audio, sample_rate = self._server.synthesize(
            text, selected_speaker, selected_language, selected_mode,
        )
        elapsed_ms = int((perf_counter() - started_at) * 1000)

        try:
            audio_path = _build_output_path(target_directory)
            _write_wav_file(audio_path, audio, sample_rate)
        except Exception as exc:
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message=f"Qwen synthesis failed while writing audio: {exc}",
            )

        return QwenSynthesisResult(
            status=QwenSynthesizerStatus.READY,
            message="Qwen synthesized audio successfully.",
            audio_path=str(audio_path),
            sample_rate=sample_rate,
            speaker=selected_speaker,
            language=selected_language,
            model_id=self._runtime_config.model_id,
            elapsed_ms=elapsed_ms,
            audio_duration_ms=_audio_duration_ms(audio, sample_rate),
        )

    def cancel_synthesis(self) -> None:
        """Kill the subprocess immediately and start reloading in the background."""
        if self._server is not None:
            self._server.cancel()
            self._server.restart_async()

    def _resolve_generation_preferences(
        self,
        *,
        speaker: str | None,
        language: str | None,
        non_streaming_mode: bool | None,
    ) -> tuple[str, str, bool]:
        selected_speaker = (speaker.strip() if speaker else None) or self._runtime_config.speaker
        selected_language = (language.strip() if language else None) or self._runtime_config.language
        selected_mode = (
            self._runtime_config.non_streaming_mode
            if non_streaming_mode is None
            else bool(non_streaming_mode)
        )
        return selected_speaker, selected_language, selected_mode


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_output_directory(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    return Path(path).expanduser().resolve()


def _resolve_target_directory(
    requested_directory: str | Path | None,
    default_directory: Path | None,
) -> Path | None:
    target_directory = _normalize_output_directory(requested_directory)
    if target_directory is None:
        target_directory = default_directory
    if target_directory is None:
        return None
    target_directory.mkdir(parents=True, exist_ok=True)
    return target_directory


def _build_output_path(output_directory: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return output_directory / f"qwen_{timestamp}.wav"


def _write_wav_file(audio_path: Path, samples: Any, sample_rate: int) -> None:
    pcm_bytes = _to_pcm16_bytes(samples)
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(int(sample_rate))
        wav_file.writeframes(pcm_bytes)


def _audio_duration_ms(samples: Any, sample_rate: int) -> int:
    if sample_rate <= 0:
        return 0
    try:
        sample_count = len(samples)
    except TypeError:
        return 0
    return int((sample_count / sample_rate) * 1000)


def _to_pcm16_bytes(samples: Any) -> bytes:
    try:
        import numpy as np
        normalized = np.asarray(samples, dtype=np.float32).reshape(-1)
        clipped = np.clip(normalized, -1.0, 1.0)
        return (clipped * 32767.0).astype(np.int16).tobytes()
    except ImportError:
        return _to_pcm16_bytes_without_numpy(samples)


def _to_pcm16_bytes_without_numpy(samples: Any) -> bytes:
    pcm_values = array("h")
    for sample in samples:
        pcm_values.append(_float_sample_to_int16(float(sample)))
    return pcm_values.tobytes()


def _float_sample_to_int16(sample: float) -> int:
    clipped = min(max(sample, -1.0), 1.0)
    return int(clipped * 32767.0)
