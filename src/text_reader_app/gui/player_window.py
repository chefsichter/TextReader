"""Player window for playback controls, status, and history navigation."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_MAX_DOTS = 12


class PlayerWindow(QWidget):
    """Compact playback window with clear status and history affordances."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextReader")
        self.resize(640, 480)
        self._is_updating_slider = False
        self._duration_ms = 0

        # Status panel
        self._capture_dot = self._build_dot()
        self._capture_status_value = QLabel("idle")
        self._playback_dot = self._build_dot()
        self._playback_status_value = QLabel("stopped")
        self._theme_button = QPushButton("Dark")
        self._theme_button.setObjectName("themeButton")
        self._theme_button.setFixedWidth(52)

        # History panel
        self._previous_history_button = QPushButton("← Prev")
        self._previous_history_button.setObjectName("historyNavButton")
        self._next_history_button = QPushButton("Next →")
        self._next_history_button.setObjectName("historyNavButton")
        self._history_position_label = QLabel("")
        self._history_position_label.setTextFormat(Qt.TextFormat.RichText)
        self._history_dots_label = QLabel("")
        self._history_dots_label.setTextFormat(Qt.TextFormat.RichText)

        # Transport panel
        self._position_label_left = QLabel("00:00")
        self._position_label_left.setObjectName("positionLabel")
        self._position_label_right = QLabel("00:00")
        self._position_label_right.setObjectName("positionLabel")
        self._position_slider = self._build_slider()
        self._jump_back_button = QPushButton("-5s")
        self._jump_back_button.setObjectName("jumpButton")
        self._play_pause_button = QPushButton("▶")
        self._play_pause_button.setObjectName("playPauseButton")
        self._jump_forward_button = QPushButton("+5s")
        self._jump_forward_button.setObjectName("jumpButton")
        self._stop_button = QPushButton("Stop")
        self._stop_button.setObjectName("stopButton")

        # Text panel
        self._entry_source_label = QLabel("-")
        self._entry_source_label.setObjectName("sourceChip")
        self._entry_meta_label = QLabel("")
        self._entry_meta_label.setObjectName("entryMetaLabel")
        self._preview = self._build_preview()

        self._build_layout()

    # ── Public setters ────────────────────────────────────────────

    def set_status_text(self, text: str) -> None:
        normalized = text.strip() or "idle"
        self._capture_status_value.setText(normalized)
        self._capture_status_value.setToolTip(normalized)
        active = normalized not in ("idle", "error", "synthesizing")
        self._set_dot_active(self._capture_dot, active)

    def set_preview_text(self, text: str) -> None:
        self._preview.setPlainText(text.strip() or "No text captured yet.")

    def set_playback_state(self, state_name: str) -> None:
        self._playback_status_value.setText(state_name)
        playing = state_name == "playing"
        self._play_pause_button.setText("⏸" if playing else "▶")
        self._set_dot_active(self._playback_dot, playing)

    def set_position_ms(self, position_ms: int) -> None:
        maximum = max(self._duration_ms, 0)
        clamped = min(max(position_ms, 0), maximum)
        self._update_slider_value(clamped)
        self._position_label_left.setText(_format_ms(clamped))

    def set_duration_ms(self, duration_ms: int) -> None:
        self._duration_ms = max(duration_ms, 0)
        self._position_slider.setRange(0, self._duration_ms)
        self._position_label_right.setText(_format_ms(self._duration_ms))
        self.set_position_ms(self._position_slider.value())

    def reset_playback_position(self) -> None:
        self._duration_ms = 0
        self._position_slider.setRange(0, 0)
        self._position_slider.setValue(0)
        self._position_label_left.setText("00:00")
        self._position_label_right.setText("00:00")

    def set_jump_labels(self, jump_seconds: int) -> None:
        s = max(jump_seconds, 0)
        self._jump_back_button.setText(f"-{s}s")
        self._jump_forward_button.setText(f"+{s}s")

    def set_transport_enabled(self, enabled: bool) -> None:
        for btn in (
            self._jump_back_button,
            self._play_pause_button,
            self._jump_forward_button,
            self._stop_button,
        ):
            btn.setEnabled(enabled)

    def set_slider_enabled(self, enabled: bool) -> None:
        self._position_slider.setEnabled(enabled)

    def set_history_position(
        self,
        current_position: int | None,
        total_entries: int,
    ) -> None:
        if not current_position or total_entries <= 0:
            self._history_position_label.setText("")
            self._history_dots_label.setText("")
            return
        self._history_position_label.setText(
            f"History <b>{current_position}</b> / {total_entries}",
        )
        self._history_dots_label.setText(
            _build_dot_html(current_position, total_entries),
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
        self._entry_source_label.setText(text.strip() or "-")

    def set_entry_context_text(self, text: str) -> None:
        self._entry_meta_label.setText(text.strip())

    def set_theme(self, theme: str) -> None:
        self._theme_button.setText("Light" if theme == "dark" else "Dark")

    # ── Signal connectors ─────────────────────────────────────────

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

    def connect_theme_toggle(self, callback: Callable[[], None]) -> None:
        self._theme_button.clicked.connect(callback)

    # ── Layout builders ───────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(self._build_status_panel())
        layout.addWidget(self._build_history_panel())
        layout.addWidget(self._build_transport_panel())
        layout.addWidget(self._build_text_panel(), 1)
        self.setLayout(layout)

    def _build_status_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("statusPanel")
        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(6)
        row.addWidget(self._capture_dot)
        row.addWidget(QLabel("Capture"))
        row.addWidget(self._capture_status_value)
        row.addSpacing(14)
        row.addWidget(self._playback_dot)
        row.addWidget(QLabel("Playback"))
        row.addWidget(self._playback_status_value)
        row.addStretch()
        row.addWidget(self._theme_button)
        return frame

    def _build_history_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("historyPanel")
        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)
        row.addWidget(self._previous_history_button)
        row.addWidget(self._history_position_label)
        row.addSpacing(4)
        row.addWidget(self._history_dots_label)
        row.addStretch()
        row.addWidget(self._next_history_button)
        self.set_history_navigation_enabled(has_previous=False, has_next=False)
        return frame

    def _build_transport_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("transportPanel")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(10)
        vbox.addLayout(self._build_slider_row())
        vbox.addLayout(self._build_controls_row())
        return frame

    def _build_slider_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._position_label_left)
        row.addWidget(self._position_slider, 1)
        row.addWidget(self._position_label_right)
        return row

    def _build_controls_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()
        row.addWidget(self._jump_back_button)
        row.addWidget(self._play_pause_button)
        row.addWidget(self._jump_forward_button)
        row.addWidget(self._stop_button)
        row.addStretch()
        return row

    def _build_text_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("textPanel")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(6)
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self._entry_source_label)
        header.addWidget(self._entry_meta_label, 1)
        vbox.addLayout(header)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("panelSeparator")
        vbox.addWidget(separator)
        vbox.addWidget(self._preview, 1)
        return frame

    def _build_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 0)
        slider.setValue(0)
        slider.setEnabled(False)
        slider.valueChanged.connect(self._sync_position_label_from_slider)
        return slider

    def _build_preview(self) -> QTextEdit:
        preview = QTextEdit()
        preview.setObjectName("textPreview")
        preview.setReadOnly(True)
        preview.setFrameShape(QFrame.Shape.NoFrame)
        preview.setPlaceholderText("Captured text will appear here.")
        return preview

    def _build_dot(self) -> QLabel:
        dot = QLabel()
        dot.setObjectName("statusDotInactive")
        dot.setFixedSize(10, 10)
        return dot

    def _set_dot_active(self, dot: QLabel, active: bool) -> None:
        name = "statusDotActive" if active else "statusDotInactive"
        dot.setObjectName(name)
        dot.style().unpolish(dot)
        dot.style().polish(dot)

    def _update_slider_value(self, value: int) -> None:
        self._is_updating_slider = True
        self._position_slider.setValue(value)
        self._is_updating_slider = False

    def _sync_position_label_from_slider(self, value: int) -> None:
        if self._is_updating_slider:
            return
        clamped = min(max(value, 0), self._duration_ms)
        self._position_label_left.setText(_format_ms(clamped))


def _format_ms(milliseconds: int) -> str:
    total_seconds = max(milliseconds, 0) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _build_dot_html(current: int, total: int) -> str:
    """Build an HTML dot-indicator string for history position."""
    visible = min(total, _MAX_DOTS)
    if total <= _MAX_DOTS:
        active_index = current - 1
    else:
        active_index = round((current - 1) / (total - 1) * (visible - 1))
    parts = []
    for i in range(visible):
        if i == active_index:
            parts.append('<span style="color:#6c5ce7;font-size:10px">●</span>')
        else:
            parts.append('<span style="color:#c0c0d8;font-size:10px">●</span>')
    return " ".join(parts)
