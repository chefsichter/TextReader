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
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


LoadCallback = Callable[[], "SettingsFormState | None"]
SaveCallback = Callable[["SettingsFormState"], None]


@dataclass(slots=True)
class SettingsFormState:
    """Flat settings snapshot used by the GUI shell and app layer."""

    capture_mode: str = "clipboard"
    hotkey_trigger: str = "Alt+L"
    jump_seconds: int = 5
    voice: str = "serena"
    language: str = "english"


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
        self._guidance_label = QLabel(
            "On GNOME/Wayland, bind a desktop shortcut to "
            "`text-reader-app --trigger-active-source` when internal hotkey registration is unavailable.",
        )
        self._capture_mode_box = QComboBox()
        self._hotkey_input = QLineEdit()
        self._jump_seconds_box = QSpinBox()
        self._voice_box = QComboBox()
        self._language_box = QComboBox()
        self._build_window()
        self.set_state(initial_state or SettingsFormState())

    def state(self) -> SettingsFormState:
        """Return the current form state."""

        return SettingsFormState(
            capture_mode=self._capture_mode_box.currentData() or "clipboard",
            hotkey_trigger=self._hotkey_input.text().strip() or "Alt+L",
            jump_seconds=self._jump_seconds_box.value(),
            voice=self._voice_box.currentText().strip() or "serena",
            language=self._language_box.currentText().strip() or "english",
        )

    def set_state(self, state: SettingsFormState) -> None:
        """Populate the form from a settings snapshot."""

        self._select_capture_mode(state.capture_mode)
        self._hotkey_input.setText(state.hotkey_trigger)
        self._jump_seconds_box.setValue(max(1, state.jump_seconds))
        self._select_combo_text(self._voice_box, state.voice)
        self._select_combo_text(self._language_box, state.language)
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

    def _build_window(self) -> None:
        self.setWindowTitle("TextReader Settings")
        self.resize(360, 220)
        self._configure_controls()
        layout = QVBoxLayout()
        layout.addLayout(self._build_form_layout())
        layout.addWidget(self._build_guidance_label())
        layout.addWidget(self._status_label)
        layout.addLayout(self._build_button_row())
        self.setLayout(layout)

    def _configure_controls(self) -> None:
        self._capture_mode_box.addItem("Clipboard", "clipboard")
        self._capture_mode_box.addItem("Selection", "selection")
        self._hotkey_input.setPlaceholderText("Alt+L")
        self._jump_seconds_box.setRange(1, 60)
        self._jump_seconds_box.setSuffix(" s")
        self._voice_box.addItems(
            ["serena", "vivian", "uncle_fu", "ryan", "aiden", "ono_anna", "sohee", "eric", "dylan"],
        )
        self._voice_box.setEditable(True)
        self._language_box.addItems(["english", "german"])
        self._language_box.setEditable(True)

    def _build_form_layout(self) -> QFormLayout:
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Capture mode", self._capture_mode_box)
        form.addRow("Hotkey", self._hotkey_input)
        form.addRow("Jump seconds", self._jump_seconds_box)
        form.addRow("Voice", self._voice_box)
        form.addRow("Language", self._language_box)
        return form

    def _build_guidance_label(self) -> QLabel:
        self._guidance_label.setWordWrap(True)
        self._guidance_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return self._guidance_label

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
            button.setDefault(True)
            button.setAutoDefault(True)
        return button

    def _select_capture_mode(self, capture_mode: str) -> None:
        normalized_mode = "selection" if capture_mode == "selection" else "clipboard"
        index = self._capture_mode_box.findData(normalized_mode, Qt.ItemDataRole.UserRole)
        self._capture_mode_box.setCurrentIndex(max(index, 0))

    def _select_combo_text(self, combo_box: QComboBox, value: str) -> None:
        index = combo_box.findText(value, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            combo_box.setCurrentIndex(index)
            return
        combo_box.setEditText(value)
