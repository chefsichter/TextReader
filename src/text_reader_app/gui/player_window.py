"""Minimal player window placeholder for the tray application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PlayerWindow(QWidget):
    """Compact placeholder window for playback controls and text preview."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextReader")
        self.resize(520, 360)
        self._status_label = QLabel("Status: idle")
        self._position_label = QLabel("00:00 / 00:00")
        self._position_slider = self._build_slider()
        self._preview = self._build_preview()
        self._build_layout()

    def set_status_text(self, text: str) -> None:
        self._status_label.setText(f"Status: {text}")

    def set_preview_text(self, text: str) -> None:
        preview = text.strip() or "No text captured yet."
        self._preview.setPlainText(preview)

    def _build_layout(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._position_slider)
        layout.addLayout(self._build_transport_row())
        layout.addWidget(self._position_label)
        layout.addWidget(self._preview)
        self.setLayout(layout)

    def _build_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 1000)
        slider.setValue(0)
        slider.setEnabled(False)
        return slider

    def _build_preview(self) -> QTextEdit:
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setPlaceholderText("Captured text will appear here.")
        return preview

    def _build_transport_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        for label in ("-5s", "Play / Pause", "+5s", "Stop"):
            row.addWidget(QPushButton(label))
        return row
