"""Background synthesis worker to keep the Qt UI responsive."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from text_reader_app.domain.models import EntryRegenerationRequest
from text_reader_app.tts import SynthesisCancelledError


class SynthesisWorkerSignals(QObject):
    """Signals emitted by one synthesis worker job."""

    finished = Signal(object, object)
    failed = Signal(object, str)
    cancelled = Signal(object)


class SynthesisWorker(QRunnable):
    """Run blocking TTS synthesis on a thread-pool thread."""

    def __init__(
        self,
        controller: object,
        history_entry: object,
        request: EntryRegenerationRequest | None = None,
    ) -> None:
        super().__init__()
        self.signals = SynthesisWorkerSignals()
        self._controller = controller
        self._history_entry = history_entry
        self._request = request
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Kill the TTS subprocess; the worker thread unblocks and emits cancelled."""
        self._controller.cancel_current_synthesis()

    def run(self) -> None:
        try:
            result = self._synthesize()
        except SynthesisCancelledError:
            self.signals.cancelled.emit(self._history_entry)
            return
        except Exception as exc:
            self.signals.failed.emit(self._history_entry, str(exc))
            return
        self.signals.finished.emit(self._history_entry, result)

    def _synthesize(self) -> object:
        if self._request is None:
            return self._controller.synthesize_text(self._history_entry.text)
        return self._controller.synthesize_text_with_overrides(self._request)
