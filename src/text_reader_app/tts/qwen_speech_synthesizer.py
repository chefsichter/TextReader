"""Qwen synthesizer shell with lazy dependency handling and WAV output."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
import wave

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
    sample_rate: int | None = None

    @property
    def ok(self) -> bool:
        """Return whether the operation succeeded."""

        return self.status == QwenSynthesizerStatus.READY


class QwenSpeechSynthesizer:
    """Lazy shell around qwen_tts that never crashes the app on import."""

    def __init__(
        self,
        runtime_config: QwenRuntimeConfig | None = None,
        output_directory: str | Path | None = None,
    ) -> None:
        self._runtime_config = runtime_config or build_default_qwen_runtime_config()
        self._output_directory = _normalize_output_directory(output_directory)
        self._backend: Any | None = None
        self._prepare_result: QwenSynthesisResult | None = None

    @property
    def runtime_config(self) -> QwenRuntimeConfig:
        """Return the configured runtime defaults."""

        return self._runtime_config

    @property
    def output_directory(self) -> Path | None:
        """Return the configured default output directory."""

        return self._output_directory

    def prepare(self) -> QwenSynthesisResult:
        """Attempt to import and initialize the Qwen backend lazily."""

        if self._prepare_result is not None:
            return self._prepare_result

        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError:
            self._prepare_result = QwenSynthesisResult(
                status=QwenSynthesizerStatus.NOT_CONFIGURED,
                message="qwen_tts or torch is not installed in the active environment.",
            )
            return self._prepare_result

        try:
            self._backend = Qwen3TTSModel.from_pretrained(
                self._runtime_config.model_id,
                dtype=_resolve_torch_dtype(torch, self._runtime_config.dtype),
                device_map="cuda",
                attn_implementation=self._runtime_config.attention_implementation,
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

    def synthesize(
        self,
        text: str,
        output_directory: str | Path | None = None,
    ) -> QwenSynthesisResult:
        """Synthesize text into a WAV file under the requested output directory."""

        if not text.strip():
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message="Cannot synthesize empty text.",
            )

        prepare_result = self.prepare()
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

        try:
            wavs, sample_rate = self._backend.generate_custom_voice(
                text,
                speaker=self._resolve_speaker(),
                language=self._runtime_config.language,
            )
            audio_path = _build_output_path(target_directory)
            _write_wav_file(audio_path, wavs[0], sample_rate)
        except Exception as exc:
            return QwenSynthesisResult(
                status=QwenSynthesizerStatus.ERROR,
                message=f"Qwen synthesis failed: {exc}",
            )

        return QwenSynthesisResult(
            status=QwenSynthesizerStatus.READY,
            message="Qwen synthesized audio successfully.",
            audio_path=str(audio_path),
            sample_rate=sample_rate,
        )

    def _resolve_speaker(self) -> str:
        speaker = self._runtime_config.speaker
        try:
            supported = self._backend.model.get_supported_speakers()
        except Exception:
            return speaker

        if speaker in supported:
            return speaker
        return list(supported)[0]


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


def _resolve_torch_dtype(torch_module: Any, dtype_name: str) -> Any:
    dtype_map = {
        "bfloat16": torch_module.bfloat16,
        "float16": torch_module.float16,
        "float32": torch_module.float32,
    }
    return dtype_map.get(dtype_name, torch_module.bfloat16)


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
