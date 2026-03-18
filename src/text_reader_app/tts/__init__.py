"""TTS exports for runtime config and synthesizer shell."""

from .qwen_runtime_config import QwenRuntimeConfig, build_default_qwen_runtime_config
from .qwen_speech_synthesizer import (
    QwenSpeechSynthesizer,
    QwenSynthesisResult,
    QwenSynthesizerStatus,
)
from .tts_subprocess import SynthesisCancelledError

__all__ = [
    "QwenRuntimeConfig",
    "QwenSpeechSynthesizer",
    "QwenSynthesisResult",
    "QwenSynthesizerStatus",
    "SynthesisCancelledError",
    "build_default_qwen_runtime_config",
]
