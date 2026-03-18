"""Minimal player window placeholder for the tray application."""

from __future__ import annotations

from collections.abc import Callable

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
        self._is_updating_slider = False
        self._duration_ms = 0
        self._position_slider = self._build_slider()
        self._jump_back_button = QPushButton("-5s")
        self._play_pause_button = QPushButton("Play")
        self._jump_forward_button = QPushButton("+5s")
        self._stop_button = QPushButton("Stop")
        self._preview = self._build_preview()
        self._build_layout()

    def set_status_text(self, text: str) -> None:
        self._status_label.setText(f"Status: {text}")

    def set_preview_text(self, text: str) -> None:
        preview = text.strip() or "No text captured yet."
        self._preview.setPlainText(preview)

    def connect_play_pause(self, callback: Callable[[], None]) -> None:
        self._play_pause_button.clicked.connect(callback)

    def connect_stop(self, callback: Callable[[], None]) -> None:
        self._stop_button.clicked.connect(callback)

    def connect_jump_backward(self, callback: Callable[[], None]) -> None:
        self._jump_back_button.clicked.connect(callback)

    def connect_jump_forward(self, callback: Callable[[], None]) -> None:
        self._jump_forward_button.clicked.connect(callback)

    def connect_seek_requested(self, callback: Callable[[int], None]) -> None:
        self._position_slider.sliderMoved.connect(callback)

    def set_transport_enabled(self, enabled: bool) -> None:
        buttons = (
            self._jump_back_button,
            self._play_pause_button,
            self._jump_forward_button,
            self._stop_button,
        )
        for button in buttons:
            button.setEnabled(enabled)

    def set_slider_enabled(self, enabled: bool) -> None:
        self._position_slider.setEnabled(enabled)

    def set_playback_state(self, state_name: str) -> None:
        if state_name == "playing":
            self._play_pause_button.setText("Pause")
            return
        self._play_pause_button.setText("Play")

    def set_position_ms(self, position_ms: int) -> None:
        maximum = max(self._duration_ms, 0)
        clamped_position = min(max(position_ms, 0), maximum)
        self._update_slider_value(clamped_position)
        self._position_label.setText(
            f"{_format_ms(clamped_position)} / {_format_ms(self._duration_ms)}",
        )

    def set_duration_ms(self, duration_ms: int) -> None:
        self._duration_ms = max(duration_ms, 0)
        self._position_slider.setRange(0, self._duration_ms)
        self.set_position_ms(self._position_slider.value())

    def reset_playback_position(self) -> None:
        self._duration_ms = 0
        self._position_slider.setRange(0, 0)
        self._position_slider.setValue(0)
        self._position_label.setText("00:00 / 00:00")

    def set_jump_labels(self, jump_seconds: int) -> None:
        seconds = max(jump_seconds, 0)
        self._jump_back_button.setText(f"-{seconds}s")
        self._jump_forward_button.setText(f"+{seconds}s")

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
        slider.setRange(0, 0)
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
        row.addWidget(self._jump_back_button)
        row.addWidget(self._play_pause_button)
        row.addWidget(self._jump_forward_button)
        row.addWidget(self._stop_button)
        return row

    def _update_slider_value(self, value: int) -> None:
        self._is_updating_slider = True
        self._position_slider.setValue(value)
        self._is_updating_slider = False


def _format_ms(milliseconds: int) -> str:
    total_seconds = max(milliseconds, 0) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"
