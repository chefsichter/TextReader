"""Compact settings window for the TextReader tray application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from text_reader_app.hotkeys import format_hotkey_trigger

from .hotkey_change_dialog import show_hotkey_dialog
from .preferences_options import (
    LANGUAGE_OPTIONS,
    READER_OPTIONS,
    SYNTHESIS_MODE_OPTIONS,
)


LoadCallback = Callable[[], "SettingsFormState | None"]
SaveCallback = Callable[["SettingsFormState"], object | None]


@dataclass(slots=True)
class SettingsFormState:
    """Flat settings snapshot used by the GUI shell and app layer."""

    capture_mode: str = "clipboard"
    hotkey_trigger: str = "Alt+L"
    jump_seconds: int = 5
    voice: str = "serena"
    language: str = "english"
    synthesis_mode: str = "whole"
    theme: str = "light"


@dataclass(slots=True)
class SettingsWindowCallbacks:
    """Hooks that can be wired by the main agent."""

    on_load_requested: LoadCallback | None = None
    on_save_requested: SaveCallback | None = None


class SettingsWindow(QWidget):
    """Small QWidget-based settings panel for the initial settings slice."""

    def __init__(
        self,
        callbacks: SettingsWindowCallbacks | None = None,
        initial_state: SettingsFormState | None = None,
    ) -> None:
        super().__init__()
        self._callbacks = callbacks or SettingsWindowCallbacks()
        self._status_label = QLabel("Settings ready.")
        self._status_label.setObjectName("statusLabel")
        self._capture_mode_box = QComboBox()
        self._hotkey_label = QLabel("Alt+L")
        self._hotkey_button = QPushButton("Change")
        self._jump_seconds_box = QSpinBox()
        self._voice_box = QComboBox()
        self._language_box = QComboBox()
        self._synthesis_mode_box = QComboBox()
        self._theme_box = QComboBox()
        self._build_window()
        self.set_state(initial_state or SettingsFormState())

    def state(self) -> SettingsFormState:
        """Return the current form state."""

        return SettingsFormState(
            capture_mode=self._capture_mode_box.currentData() or "clipboard",
            hotkey_trigger=self._hotkey_label.text().strip() or "Alt+L",
            jump_seconds=self._jump_seconds_box.value(),
            voice=self._voice_box.currentText().strip() or "serena",
            language=self._language_box.currentText().strip() or "english",
            synthesis_mode=self._synthesis_mode_box.currentData() or "whole",
            theme=self._theme_box.currentData() or "light",
        )

    def set_state(self, state: SettingsFormState) -> None:
        """Populate the form from a settings snapshot."""

        self._select_capture_mode(state.capture_mode)
        self._hotkey_label.setText(format_hotkey_trigger(state.hotkey_trigger))
        self._jump_seconds_box.setValue(max(1, state.jump_seconds))
        self._select_combo_text(self._voice_box, state.voice)
        self._select_combo_text(self._language_box, state.language)
        self._select_synthesis_mode(state.synthesis_mode)
        self._select_theme(state.theme)
        self.set_status_text("Settings loaded.")

    def set_status_text(self, text: str) -> None:
        """Update the inline status line."""

        self._status_label.setText(text)

    def request_load(self) -> None:
        """Load settings from the app layer if a hook exists."""

        if self._callbacks.on_load_requested is None:
            self.set_status_text("Load hook is not wired yet.")
            return
        loaded_state = self._callbacks.on_load_requested()
        if loaded_state is None:
            self.set_status_text("No saved settings were returned.")
            return
        self.set_state(loaded_state)

    def request_save(self) -> None:
        """Push the current state to the app layer if a hook exists."""

        if self._callbacks.on_save_requested is None:
            self.set_status_text("Save hook is not wired yet.")
            return
        self._callbacks.on_save_requested(self.state())
        self.set_status_text("Settings saved.")

    def set_save_callback(self, callback: SaveCallback | None) -> None:
        """Replace the save callback after construction when wiring the GUI."""

        self._callbacks.on_save_requested = callback

    def save_callback(self) -> SaveCallback | None:
        """Return the current save callback."""

        return self._callbacks.on_save_requested

    def change_hotkey(self) -> None:
        """Open the hotkey capture dialog from external GUI actions."""

        self._change_hotkey()

    def set_reader(self, reader: str) -> None:
        """Update the reader combo without touching unrelated settings."""

        self._select_combo_text(self._voice_box, reader)

    def set_language(self, language: str) -> None:
        """Update the language combo without touching unrelated settings."""

        self._select_combo_text(self._language_box, language)

    def set_synthesis_mode(self, synthesis_mode: str) -> None:
        """Update the synthesis mode combo without touching unrelated settings."""

        self._select_synthesis_mode(synthesis_mode)

    def _build_window(self) -> None:
        self.setWindowTitle("TextReader Settings")
        self.resize(360, 250)
        self._configure_controls()
        layout = QVBoxLayout()
        layout.addLayout(self._build_form_layout())
        layout.addWidget(self._status_label)
        layout.addLayout(self._build_button_row())
        self.setLayout(layout)

    def _configure_controls(self) -> None:
        self._capture_mode_box.addItem("Clipboard", "clipboard")
        self._capture_mode_box.addItem("Selection", "selection")
        self._hotkey_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._hotkey_button.clicked.connect(self._change_hotkey)
        self._jump_seconds_box.setRange(1, 60)
        self._jump_seconds_box.setSuffix(" s")
        self._voice_box.addItems(list(READER_OPTIONS))
        self._voice_box.setEditable(True)
        self._language_box.addItems(list(LANGUAGE_OPTIONS))
        self._language_box.setEditable(True)
        for value, label in SYNTHESIS_MODE_OPTIONS:
            self._synthesis_mode_box.addItem(label, value)
        self._theme_box.addItem("Light", "light")
        self._theme_box.addItem("Dark", "dark")

    def _build_form_layout(self) -> QFormLayout:
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Capture mode", self._capture_mode_box)
        form.addRow("Hotkey", self._build_hotkey_row())
        form.addRow("Jump seconds", self._jump_seconds_box)
        form.addRow("Reader", self._voice_box)
        form.addRow("Language", self._language_box)
        form.addRow("Synthesis", self._synthesis_mode_box)
        form.addRow("Theme", self._theme_box)
        return form

    def _build_hotkey_row(self) -> QWidget:
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._hotkey_label, 1)
        row.addWidget(self._hotkey_button)
        return container

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._build_button("Reload", self.request_load))
        row.addStretch(1)
        row.addWidget(self._build_button("Save", self.request_save, primary=True))
        return row

    def _build_button(
        self,
        text: str,
        callback: Callable[[], None],
        *,
        primary: bool = False,
    ) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        if primary:
            button.setObjectName("primaryButton")
            button.setDefault(True)
            button.setAutoDefault(True)
        return button

    def _select_capture_mode(self, capture_mode: str) -> None:
        normalized_mode = "selection" if capture_mode == "selection" else "clipboard"
        index = self._capture_mode_box.findData(normalized_mode, Qt.ItemDataRole.UserRole)
        self._capture_mode_box.setCurrentIndex(max(index, 0))

    def _select_theme(self, theme: str) -> None:
        normalized = "dark" if theme == "dark" else "light"
        index = self._theme_box.findData(normalized, Qt.ItemDataRole.UserRole)
        self._theme_box.setCurrentIndex(max(index, 0))

    def _select_synthesis_mode(self, synthesis_mode: str) -> None:
        normalized = "streaming" if synthesis_mode == "streaming" else "whole"
        index = self._synthesis_mode_box.findData(normalized, Qt.ItemDataRole.UserRole)
        self._synthesis_mode_box.setCurrentIndex(max(index, 0))

    def _select_combo_text(self, combo_box: QComboBox, value: str) -> None:
        index = combo_box.findText(value, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            combo_box.setCurrentIndex(index)
            return
        combo_box.setEditText(value)

    def _change_hotkey(self) -> None:
        updated_trigger = show_hotkey_dialog(
            parent=self,
            current_trigger=self._hotkey_label.text(),
        )
        if updated_trigger is None:
            return
        self._hotkey_label.setText(updated_trigger)
        self.set_status_text("Hotkey updated. Save to apply it.")
