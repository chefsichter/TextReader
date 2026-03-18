"""Player window for playback controls, status, and history navigation."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PlayerWindow(QWidget):
    """Compact playback window with clear status and history affordances."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextReader")
        self.resize(640, 440)
        self._title_label = QLabel("TextReader")
        self._capture_status_value = self._build_value_label("idle")
        self._playback_status_value = self._build_value_label("stopped")
        self._history_position_label = self._build_value_label("No history yet")
        self._entry_meta_label = self._build_secondary_label("No capture loaded.")
        self._entry_source_label = self._build_secondary_label("Source: -")
        self._position_label = QLabel("00:00 / 00:00")
        self._is_updating_slider = False
        self._duration_ms = 0
        self._position_slider = self._build_slider()
        self._previous_history_button = QPushButton("Previous")
        self._next_history_button = QPushButton("Next")
        self._jump_back_button = QPushButton("-5s")
        self._play_pause_button = QPushButton("Play")
        self._jump_forward_button = QPushButton("+5s")
        self._stop_button = QPushButton("Stop")
        self._preview = self._build_preview()
        self._build_layout()

    def set_status_text(self, text: str) -> None:
        normalized_text = text.strip() or "idle"
        self._capture_status_value.setText(normalized_text)
        self._capture_status_value.setToolTip(normalized_text)

    def set_preview_text(self, text: str) -> None:
        preview = text.strip() or "No text captured yet."
        self._preview.setPlainText(preview)
        self._entry_meta_label.setText(_preview_summary(preview))

    def connect_play_pause(self, callback: Callable[[], None]) -> None:
        self._play_pause_button.clicked.connect(callback)

    def connect_previous_history(self, callback: Callable[[], None]) -> None:
        self._previous_history_button.clicked.connect(callback)

    def connect_next_history(self, callback: Callable[[], None]) -> None:
        self._next_history_button.clicked.connect(callback)

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
        self._playback_status_value.setText(state_name)
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

    def set_history_position(
        self,
        current_position: int | None,
        total_entries: int,
    ) -> None:
        if not current_position or total_entries <= 0:
            self._history_position_label.setText("No history yet")
            return
        self._history_position_label.setText(
            f"History {current_position} / {total_entries}",
        )

    def set_history_navigation_enabled(
        self,
        *,
        has_previous: bool,
        has_next: bool,
    ) -> None:
        self._previous_history_button.setEnabled(has_previous)
        self._next_history_button.setEnabled(has_next)

    def set_entry_source_text(self, text: str) -> None:
        normalized_text = text.strip() or "-"
        self._entry_source_label.setText(f"Source: {normalized_text}")

    def set_entry_context_text(self, text: str) -> None:
        normalized_text = text.strip() or "No capture loaded."
        self._entry_meta_label.setText(normalized_text)

    def _build_layout(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_status_panel())
        layout.addWidget(self._build_history_panel())
        layout.addWidget(self._position_slider)
        layout.addLayout(self._build_transport_row())
        layout.addWidget(self._position_label)
        layout.addWidget(self._entry_source_label)
        layout.addWidget(self._entry_meta_label)
        layout.addWidget(self._preview)
        self.setLayout(layout)

    def _build_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 0)
        slider.setValue(0)
        slider.setEnabled(False)
        slider.valueChanged.connect(self._sync_position_label_from_slider)
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

    def _build_header(self) -> QLabel:
        self._title_label.setObjectName("playerTitle")
        return self._title_label

    def _build_status_panel(self) -> QFrame:
        frame = QFrame()
        layout = QGridLayout()
        layout.addWidget(QLabel("Capture status"), 0, 0)
        layout.addWidget(self._capture_status_value, 0, 1)
        layout.addWidget(QLabel("Playback"), 1, 0)
        layout.addWidget(self._playback_status_value, 1, 1)
        frame.setLayout(layout)
        return frame

    def _build_history_panel(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout()
        layout.addWidget(self._previous_history_button)
        layout.addWidget(self._history_position_label, 1)
        layout.addWidget(self._next_history_button)
        frame.setLayout(layout)
        self.set_history_navigation_enabled(has_previous=False, has_next=False)
        return frame

    def _build_value_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _build_secondary_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _update_slider_value(self, value: int) -> None:
        self._is_updating_slider = True
        self._position_slider.setValue(value)
        self._is_updating_slider = False

    def _sync_position_label_from_slider(self, value: int) -> None:
        if self._is_updating_slider:
            return
        clamped_value = min(max(value, 0), self._duration_ms)
        self._position_label.setText(
            f"{_format_ms(clamped_value)} / {_format_ms(self._duration_ms)}",
        )


def _format_ms(milliseconds: int) -> str:
    total_seconds = max(milliseconds, 0) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _preview_summary(preview: str) -> str:
    first_line = preview.splitlines()[0].strip()
    if not first_line:
        return "No capture loaded."
    summary = first_line[:96]
    if len(first_line) > len(summary):
        return f"{summary}..."
    return summary
