"""Player window for playback controls, status, and history navigation."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QStyleFactory,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .preferences_options import language_info_text, reader_info_text

_MAX_DOTS = 14
_PANEL_BG_LIGHT = "#ffffff"
_PANEL_BG_DARK = "#22223a"


class _FadeOverlay(QWidget):
    """Gradient overlay that fades text content out at the bottom."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hex_bg = _PANEL_BG_LIGHT

    def set_bg_color(self, hex_color: str) -> None:
        self._hex_bg = hex_color
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        transparent = QColor(self._hex_bg)
        transparent.setAlpha(0)
        opaque = QColor(self._hex_bg)
        opaque.setAlpha(215)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(1.0, opaque)
        painter.fillRect(self.rect(), gradient)


class _PreviewArea(QWidget):
    """QTextEdit with bottom fade-out and a scroll-to-bottom indicator."""

    _FADE_H = 52
    _BTN_SIZE = 30

    def __init__(self) -> None:
        super().__init__()
        self._edit = QTextEdit(self)
        self._edit.setObjectName("textPreview")
        self._edit.setReadOnly(True)
        self._edit.setFrameShape(QFrame.Shape.NoFrame)
        self._edit.setPlaceholderText("Captured text will appear here.")

        self._fade = _FadeOverlay(self)

        self._scroll_btn = QPushButton("↓", self)
        self._scroll_btn.setObjectName("scrollDownButton")
        self._scroll_btn.setFixedSize(self._BTN_SIZE, self._BTN_SIZE)
        self._scroll_btn.clicked.connect(self._scroll_to_bottom)
        self._scroll_btn.hide()
        self._fade.hide()

        sb = self._edit.verticalScrollBar()
        sb.valueChanged.connect(self._sync_scroll_state)
        sb.rangeChanged.connect(lambda _lo, _hi: self._sync_scroll_state(sb.value()))

    @property
    def text_edit(self) -> QTextEdit:
        return self._edit

    def set_bg_color(self, hex_color: str) -> None:
        self._fade.set_bg_color(hex_color)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._edit.setGeometry(0, 0, w, h)
        self._fade.setGeometry(0, h - self._FADE_H, w, self._FADE_H)
        self._scroll_btn.move((w - self._BTN_SIZE) // 2, h - self._BTN_SIZE - 8)

    def _sync_scroll_state(self, value: int) -> None:
        sb = self._edit.verticalScrollBar()
        scrollable = sb.maximum() > 0
        at_bottom = value >= sb.maximum() - 2
        show = scrollable and not at_bottom
        self._scroll_btn.setVisible(show)
        self._fade.setVisible(show)

    def _scroll_to_bottom(self) -> None:
        self._edit.verticalScrollBar().setValue(
            self._edit.verticalScrollBar().maximum(),
        )


class PlayerWindow(QWidget):
    """Compact playback window with clear status and history affordances."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextReader")
        self.resize(640, 480)
        self._is_updating_slider = False
        self._duration_ms = 0
        self._synthesis_in_progress = False

        # Status panel
        self._capture_dot = self._build_dot()
        self._capture_status_value = QLabel("idle")
        self._playback_dot = self._build_dot()
        self._playback_status_value = QLabel("stopped")
        self._synthesis_progress_bar = QProgressBar()
        self._synthesis_progress_bar.setObjectName("synthesisProgressBar")
        self._synthesis_progress_bar.setRange(0, 100)
        self._synthesis_progress_bar.setValue(0)
        self._synthesis_progress_bar.hide()
        self._synthesis_progress_label = QLabel("")
        self._synthesis_progress_label.setObjectName("statusLabel")
        self._synthesis_progress_label.hide()
        self._cancel_synthesis_button = QPushButton("✕")
        self._cancel_synthesis_button.setObjectName("cancelSynthesisButton")
        self._cancel_synthesis_button.setToolTip("Cancel synthesis")
        self._cancel_synthesis_button.hide()
        self._theme_button = QPushButton("☾")
        self._theme_button.setObjectName("themeButton")
        self._theme_button.setFixedWidth(30)

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
        self._source_badge = QLabel("-")
        self._source_badge.setObjectName("sourceChip")
        self._voice_badge = QLabel("")
        self._voice_badge.setObjectName("voiceBadge")
        self._voice_badge.hide()
        self._language_badge = QLabel("")
        self._language_badge.setObjectName("languageBadge")
        self._language_badge.hide()
        self._timestamp_label = QLabel("")
        self._timestamp_label.setObjectName("entryTimestamp")
        self._edit_regenerate_button = QPushButton("✎")
        self._edit_regenerate_button.setObjectName("historyActionButton")
        self._edit_regenerate_button.setToolTip(
            "Edit the current text, reader, or language and regenerate audio.",
        )
        self._download_audio_button = QPushButton("⬇")
        self._download_audio_button.setObjectName("historyActionButton")
        self._download_audio_button.setToolTip(
            "Save the generated audio file for the current entry to another location.",
        )
        self._delete_entry_button = QPushButton("🗑")
        self._delete_entry_button.setObjectName("historyActionButton")
        self._delete_entry_button.setToolTip(
            "Delete the current entry and its generated audio file.",
        )
        self._clear_history_button = QPushButton("🧹")
        self._clear_history_button.setObjectName("historyActionButton")
        self._clear_history_button.setToolTip(
            "Delete all saved entries and all generated audio files after confirmation.",
        )
        self._preview_area = _PreviewArea()

        self._build_layout()

    # ── Public setters ────────────────────────────────────────────

    def set_status_text(self, text: str) -> None:
        normalized = text.strip() or "idle"
        self._capture_status_value.setText(normalized)
        self._capture_status_value.setToolTip(normalized)
        if normalized == "synthesizing":
            self._set_dot_state(self._capture_dot, "working")
            return
        active = normalized not in ("idle", "error")
        self._set_dot_state(self._capture_dot, "active" if active else "inactive")

    def set_preview_text(self, text: str) -> None:
        self._preview_area.text_edit.setPlainText(
            text.strip() or "No text captured yet.",
        )

    def set_playback_state(self, state_name: str) -> None:
        self._playback_status_value.setText(state_name)
        playing = state_name == "playing"
        self._play_pause_button.setText("⏸" if playing else "▶")
        self._set_dot_state(self._playback_dot, "active" if playing else "inactive")

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
        effective_enabled = enabled and not self._synthesis_in_progress
        for btn in (
            self._jump_back_button,
            self._play_pause_button,
            self._jump_forward_button,
            self._stop_button,
        ):
            btn.setEnabled(effective_enabled)

    def set_slider_enabled(self, enabled: bool) -> None:
        self._position_slider.setEnabled(enabled and not self._synthesis_in_progress)

    def set_synthesis_in_progress(self, in_progress: bool) -> None:
        self._synthesis_in_progress = in_progress
        if not in_progress:
            return
        self.set_transport_enabled(False)
        self.set_slider_enabled(False)

    def set_synthesis_progress(self, progress_percent: int, detail_text: str) -> None:
        self._synthesis_progress_bar.show()
        self._synthesis_progress_label.show()
        self._cancel_synthesis_button.show()
        self._synthesis_progress_bar.setValue(min(max(progress_percent, 0), 100))
        self._synthesis_progress_label.setText(detail_text)

    def set_synthesis_summary(
        self,
        elapsed_ms: int | None,
        audio_duration_ms: int | None,
    ) -> None:
        if elapsed_ms is None or audio_duration_ms is None:
            self.clear_synthesis_progress()
            return
        self._synthesis_progress_bar.show()
        self._synthesis_progress_bar.setValue(100)
        self._synthesis_progress_label.show()
        self._synthesis_progress_label.setText(
            f"{_format_seconds(elapsed_ms)} for {_format_seconds(audio_duration_ms)} audio",
        )

    def clear_synthesis_progress(self) -> None:
        self._synthesis_progress_bar.hide()
        self._synthesis_progress_bar.setValue(0)
        self._synthesis_progress_label.hide()
        self._synthesis_progress_label.clear()
        self._cancel_synthesis_button.hide()

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
        normalized = text.strip() or "-"
        self._source_badge.setText(normalized)
        self._source_badge.setToolTip(f"Source: {normalized}" if normalized != "-" else "")

    def set_entry_context_text(self, text: str) -> None:
        """Parse 'timestamp | voice=X | language=Y' and show as badges."""
        timestamp, voice, language = _parse_context_text(text)
        self._timestamp_label.setText(timestamp)
        self._voice_badge.setText(voice)
        self._voice_badge.setVisible(bool(voice))
        self._voice_badge.setToolTip(reader_info_text(voice))
        self._language_badge.setText(language)
        self._language_badge.setVisible(bool(language))
        self._language_badge.setToolTip(language_info_text(language))

    def set_theme(self, theme: str) -> None:
        self._theme_button.setText("☀" if theme == "dark" else "☾")
        panel_bg = _PANEL_BG_DARK if theme == "dark" else _PANEL_BG_LIGHT
        self._preview_area.set_bg_color(panel_bg)

    def set_entry_actions_enabled(
        self,
        *,
        has_audio: bool,
        has_entry: bool,
        has_history: bool,
    ) -> None:
        self._edit_regenerate_button.setEnabled(has_entry)
        self._download_audio_button.setEnabled(has_audio)
        self._delete_entry_button.setEnabled(has_entry)
        self._clear_history_button.setEnabled(has_history)

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

    def connect_download_audio(self, callback: Callable[[], None]) -> None:
        self._download_audio_button.clicked.connect(callback)

    def connect_edit_regenerate(self, callback: Callable[[], None]) -> None:
        self._edit_regenerate_button.clicked.connect(callback)

    def connect_delete_current_entry(self, callback: Callable[[], None]) -> None:
        self._delete_entry_button.clicked.connect(callback)

    def connect_clear_history(self, callback: Callable[[], None]) -> None:
        self._clear_history_button.clicked.connect(callback)

    def connect_cancel_synthesis(self, callback: Callable[[], None]) -> None:
        self._cancel_synthesis_button.clicked.connect(callback)

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
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(8)
        row = QHBoxLayout()
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
        layout.addLayout(row)
        layout.addLayout(self._build_synthesis_progress_row())
        return frame

    def _build_synthesis_progress_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._synthesis_progress_bar, 1)
        row.addWidget(self._synthesis_progress_label)
        row.addWidget(self._cancel_synthesis_button)
        return row

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
        vbox.addLayout(self._build_badge_row())
        vbox.addLayout(self._build_entry_action_row())
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("panelSeparator")
        vbox.addWidget(separator)
        vbox.addWidget(self._preview_area, 1)
        return frame

    def _build_badge_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._source_badge)
        row.addWidget(self._voice_badge)
        row.addWidget(self._language_badge)
        row.addWidget(self._timestamp_label)
        row.addStretch()
        return row

    def _build_entry_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        row.addWidget(self._edit_regenerate_button)
        row.addWidget(self._download_audio_button)
        row.addWidget(self._delete_entry_button)
        row.addWidget(self._clear_history_button)
        self.set_entry_actions_enabled(
            has_audio=False,
            has_entry=False,
            has_history=False,
        )
        return row

    def _build_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            slider.setStyle(fusion)
        slider.setRange(0, 0)
        slider.setValue(0)
        slider.setEnabled(False)
        slider.valueChanged.connect(self._sync_position_label_from_slider)
        return slider

    def _build_dot(self) -> QLabel:
        dot = QLabel()
        dot.setObjectName("statusDotInactive")
        dot.setFixedSize(10, 10)
        return dot

    def _set_dot_state(self, dot: QLabel, state: str) -> None:
        if state == "working":
            name = "statusDotWorking"
        elif state == "active":
            name = "statusDotActive"
        else:
            name = "statusDotInactive"
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


def _format_seconds(milliseconds: int) -> str:
    total_s = max(milliseconds, 0) / 1000
    if total_s < 60:
        return f"{total_s:.1f}s"
    total_s_int = int(total_s)
    if total_s_int < 3600:
        m, s = divmod(total_s_int, 60)
        return f"{m}m {s}s"
    h, remainder = divmod(total_s_int, 3600)
    m, s = divmod(remainder, 60)
    return f"{h}h {m}m {s}s"


def _parse_context_text(text: str) -> tuple[str, str, str]:
    """Parse 'YYYY-MM-DD HH:MM:SS | voice=X | language=Y' into components."""
    voice = ""
    language = ""
    timestamp_raw = ""
    for part in text.split("|"):
        part = part.strip()
        if "=" in part:
            key, _, val = part.partition("=")
            key = key.strip()
            if key == "voice":
                voice = val.strip()
            elif key == "language":
                language = val.strip()
        else:
            timestamp_raw = part
    # Format "2026-03-18 14:38:26" → "2026-03-18 · 14:38:26"
    timestamp = timestamp_raw.replace(" ", " · ", 1) if timestamp_raw else ""
    return timestamp, voice, language


def _build_dot_html(current: int, total: int) -> str:
    """Build HTML dot-indicator: active dot as pill (▬), others as bullets (●)."""
    visible = min(total, _MAX_DOTS)
    if total <= _MAX_DOTS:
        active_index = current - 1
    else:
        active_index = round((current - 1) / (total - 1) * (visible - 1))
    parts = []
    for i in range(visible):
        if i == active_index:
            parts.append(
                '<span style="color:#6c5ce7;font-size:13px;letter-spacing:-1px">▬</span>'
            )
        else:
            parts.append('<span style="color:#c0c0d8;font-size:9px">●</span>')
    return "&thinsp;".join(parts)
