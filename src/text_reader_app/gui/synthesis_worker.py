"""Background synthesis worker to keep the Qt UI responsive."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal


class SynthesisWorkerSignals(QObject):
    """Signals emitted by one synthesis worker job."""

    finished = Signal(object, object)
    failed = Signal(object, str)


class SynthesisWorker(QRunnable):
    """Run blocking TTS synthesis on a thread-pool thread."""

    def __init__(self, controller: object, history_entry: object) -> None:
        super().__init__()
        self.signals = SynthesisWorkerSignals()
        self._controller = controller
        self._history_entry = history_entry
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            result = self._controller.synthesize_text(self._history_entry.text)
        except Exception as exc:
            self.signals.failed.emit(self._history_entry, str(exc))
            return
        self.signals.finished.emit(self._history_entry, result)
