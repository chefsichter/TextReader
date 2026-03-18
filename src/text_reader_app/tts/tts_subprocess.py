"""Persistent TTS model subprocess with queue-based IPC.

The model is loaded once in a dedicated subprocess.  Synthesis requests are
sent via a multiprocessing Queue and results are returned the same way.
Cancelling synthesis is immediate: the subprocess is killed (SIGTERM/SIGKILL)
and a fresh one is spawned in the background so the model is ready for the
next request without blocking the UI.
"""

from __future__ import annotations

import queue as _queue
import multiprocessing
import threading
from pathlib import Path
from typing import Any


class SynthesisCancelledError(Exception):
    """Raised in the worker thread when synthesis was cancelled."""


# ── Subprocess entry point ────────────────────────────────────────────────────

def _model_worker(
    config: dict,
    request_queue: Any,
    result_queue: Any,
) -> None:
    """Runs inside the subprocess: load model once, then serve requests."""
    import os

    # Apply env vars before importing torch.
    hsa = config.get("hsa_enable_sdma")
    if hsa is not None:
        os.environ["HSA_ENABLE_SDMA"] = str(hsa)
    if config.get("disable_tunableop", True):
        os.environ["PYTORCH_TUNABLEOP_ENABLED"] = "0"
    miopen = config.get("miopen_cache_dir")
    if miopen:
        Path(miopen).mkdir(parents=True, exist_ok=True)
        os.environ["MIOPEN_USER_DB_PATH"] = miopen
        os.environ.setdefault("MIOPEN_FIND_MODE", "2")
    inductor = config.get("torch_compile_cache_dir")
    if inductor:
        Path(inductor).mkdir(parents=True, exist_ok=True)
        os.environ["TORCHINDUCTOR_CACHE_DIR"] = inductor

    try:
        import torch
        from qwen_tts import Qwen3TTSModel

        _dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        dtype = _dtype_map.get(config["dtype"], torch.bfloat16)
        model = Qwen3TTSModel.from_pretrained(
            config["model_id"],
            dtype=dtype,
            device_map="cuda",
            attn_implementation=config["attention_implementation"],
        )
        if config.get("enable_torch_compile", True):
            try:
                model = torch.compile(model)
            except Exception:
                pass
        try:
            model.generate_custom_voice(
                "Warmup.",
                speaker=config["speaker"],
                language=config["language"],
                non_streaming_mode=True,
            )
        except Exception:
            pass
    except Exception as exc:
        result_queue.put(("error", str(exc)))
        return

    result_queue.put(("ready",))

    while True:
        try:
            request = request_queue.get()
        except Exception:
            break
        if request[0] == "stop":
            break
        if request[0] == "synthesize":
            _, text, speaker, language, non_streaming_mode = request
            try:
                import numpy as np
                wavs, sr = model.generate_custom_voice(
                    text,
                    speaker=speaker,
                    language=language,
                    non_streaming_mode=non_streaming_mode,
                )
                audio = np.asarray(wavs[0], dtype=np.float32)
                result_queue.put(("ok", audio, int(sr)))
            except Exception as exc:
                result_queue.put(("error", str(exc)))


# ── Server (main-process side) ────────────────────────────────────────────────

class TTSModelServer:
    """Manages a persistent TTS subprocess.

    Thread-safety: ``ensure_ready`` and ``synthesize`` are called from a
    QThreadPool worker thread.  ``cancel`` and ``restart_async`` are called
    from the Qt main thread.  A ``threading.Lock`` guards all state changes.
    """

    def __init__(self, config: Any) -> None:
        self._config = _config_to_dict(config)
        self._process: Any = None
        self._request_queue: Any = None
        self._result_queue: Any = None
        # State: "idle" | "starting" | "ready"
        self._state = "idle"
        self._start_error: str | None = None
        self._lock = threading.Lock()
        self._ready_event = threading.Event()
        self._cancelled_event = threading.Event()

    # ── Public API ────────────────────────────────────────────────

    def ensure_ready(self) -> str | None:
        """Block until the subprocess is ready.  Returns an error string or None.

        Raises ``SynthesisCancelledError`` if ``cancel()`` was called while
        waiting (e.g. cancel during initial model load).
        """
        with self._lock:
            if self._state == "ready" and self._is_alive():
                return None
            if self._state == "idle":
                self._begin_start_locked()
            # If "starting", fall through and wait.

        self._ready_event.wait(timeout=300)

        if self._cancelled_event.is_set():
            raise SynthesisCancelledError()
        return self._start_error

    def synthesize(
        self,
        text: str,
        speaker: str,
        language: str,
        non_streaming_mode: bool,
    ) -> tuple[Any, int]:
        """Send a synthesis request and block until the result arrives.

        Raises ``SynthesisCancelledError`` when the subprocess was killed.
        Raises ``RuntimeError`` on synthesis error or unexpected subprocess death.
        """
        assert self._request_queue is not None and self._result_queue is not None
        self._request_queue.put(("synthesize", text, speaker, language, non_streaming_mode))
        while True:
            try:
                result = self._result_queue.get(timeout=5)
                break
            except _queue.Empty:
                if not self._is_alive():
                    raise RuntimeError("TTS subprocess died unexpectedly during synthesis.")
        if result[0] == "cancelled":
            raise SynthesisCancelledError()
        if result[0] == "error":
            raise RuntimeError(result[1])
        return result[1], result[2]  # numpy array, sample_rate

    def cancel(self) -> None:
        """Kill the subprocess immediately.

        Unblocks any thread waiting in ``synthesize()`` or ``ensure_ready()``.
        Call ``restart_async()`` afterwards to spawn a fresh subprocess.
        """
        with self._lock:
            self._state = "idle"
            self._cancelled_event.set()
            process = self._process
            result_queue = self._result_queue
            self._process = None

        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=3)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)

        # Unblock synthesize() if it's waiting on result_queue.get().
        if result_queue is not None:
            try:
                result_queue.put_nowait(("cancelled",))
            except Exception:
                pass

        # Unblock ensure_ready() if it's waiting on _ready_event.
        self._ready_event.set()

    def restart_async(self) -> None:
        """Spawn a fresh subprocess in the background.

        Call this after ``cancel()`` so the model is ready for the next
        synthesis request without blocking the UI.
        """
        with self._lock:
            self._cancelled_event.clear()
            self._state = "idle"
            self._ready_event.clear()
            self._start_error = None
            self._begin_start_locked()

    # ── Internal ──────────────────────────────────────────────────

    def _begin_start_locked(self) -> None:
        """Transition to 'starting' and spawn the load thread.  Lock must be held."""
        self._state = "starting"
        self._ready_event.clear()
        self._start_error = None
        threading.Thread(target=self._start_blocking, daemon=True).start()

    def _start_blocking(self) -> None:
        """Spawn the subprocess and wait for its ready signal.  Runs in a daemon thread."""
        ctx = multiprocessing.get_context("spawn")
        req_q = ctx.Queue()
        res_q = ctx.Queue()

        # Store queues early so cancel() can put a sentinel even during load.
        with self._lock:
            if self._state != "starting":
                self._ready_event.set()
                return
            self._request_queue = req_q
            self._result_queue = res_q

        process = ctx.Process(
            target=_model_worker,
            args=(self._config, req_q, res_q),
            daemon=True,
        )
        process.start()

        # Wait for the subprocess to signal ready or error.
        msg: tuple
        while True:
            try:
                msg = res_q.get(timeout=5)
                break
            except _queue.Empty:
                if not process.is_alive():
                    msg = ("error", "Model worker process died during startup.")
                    break

        with self._lock:
            if self._state != "starting":
                # cancel() was called while we were loading — discard this process.
                process.terminate()
                self._ready_event.set()
                return
            if msg[0] == "error":
                self._start_error = msg[1]
                self._state = "idle"
                process.terminate()
            else:
                self._process = process
                self._state = "ready"
            self._ready_event.set()

    def _is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config_to_dict(config: Any) -> dict:
    return {
        "model_id": config.model_id,
        "dtype": config.dtype,
        "attention_implementation": config.attention_implementation,
        "speaker": config.speaker,
        "language": config.language,
        "enable_torch_compile": config.enable_torch_compile,
        "disable_tunableop": config.disable_tunableop,
        "hsa_enable_sdma": config.hsa_enable_sdma,
        "miopen_cache_dir": str(config.miopen_cache_dir) if config.miopen_cache_dir else None,
        "torch_compile_cache_dir": (
            str(config.torch_compile_cache_dir) if config.torch_compile_cache_dir else None
        ),
    }
