"""Default Qwen runtime settings for the initial scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class QwenRuntimeConfig:
    """Static runtime defaults derived from local benchmark results."""

    model_id: str
    dtype: str
    attention_implementation: str
    speaker: str
    language: str
    non_streaming_mode: bool = True
    enable_torch_compile: bool = False
    disable_tunableop: bool = True
    hsa_enable_sdma: int | None = 0


def build_default_qwen_runtime_config() -> QwenRuntimeConfig:
    """Return the preferred Linux runtime config from the benchmark notes."""

    return QwenRuntimeConfig(
        model_id="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        dtype="bfloat16",
        attention_implementation="sdpa",
        speaker="serena",
        language="german",
    )
