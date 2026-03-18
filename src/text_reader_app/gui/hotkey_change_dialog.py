"""Dialog for capturing a new hotkey combination from the user."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from text_reader_app.hotkeys import format_hotkey_trigger

from .style_loader import load_app_icon


class HotkeyChangeDialog(QDialog):
    """Styled dialog for capturing one hotkey combination."""

    def __init__(
        self,
        *,
        current_trigger: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_label = QLabel("Enter a new hotkey:")
        self._sequence_edit = QKeySequenceEdit(self)
        self._hint_label = QLabel("Allowed: Alt, Ctrl, Shift, Meta plus one key.")
        self._cancel_button = QPushButton("Cancel")
        self._confirm_button = QPushButton("OK")
        self._build_dialog(current_trigger)

    def trigger(self) -> str | None:
        """Return the normalized trigger string for the current sequence."""

        trigger = _trigger_from_sequence(self._sequence_edit.keySequence())
        if trigger is None:
            return None
        return format_hotkey_trigger(trigger)

    def _build_dialog(self, current_trigger: str) -> None:
        self.setWindowTitle("Change Hotkey")
        self.setWindowIcon(load_app_icon())
        self.resize(400, 190)
        self._configure_controls(current_trigger)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(self._build_panel(), 1)
        layout.addLayout(self._build_button_row())

    def _configure_controls(self, current_trigger: str) -> None:
        self._sequence_edit.setKeySequence(QKeySequence(current_trigger))
        self._title_label.setObjectName("dialogMessageLabel")
        self._hint_label.setWordWrap(True)
        self._hint_label.setObjectName("dialogHintLabel")
        self._hint_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._cancel_button.clicked.connect(self.reject)
        self._confirm_button.setObjectName("primaryButton")
        self._confirm_button.clicked.connect(self.accept)

    def _build_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("dialogPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self._title_label)
        layout.addWidget(self._sequence_edit)
        layout.addWidget(self._hint_label)
        return frame

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self._cancel_button)
        row.addWidget(self._confirm_button)
        return row


def show_hotkey_dialog(
    parent: QWidget | None = None,
    current_trigger: str = "Alt+L",
) -> str | None:
    """Capture one hotkey combination and return it as ``Alt+L`` style text."""

    dialog = HotkeyChangeDialog(current_trigger=current_trigger, parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.trigger()


def _trigger_from_sequence(sequence: QKeySequence) -> str | None:
    if sequence.isEmpty():
        return None
    combo = sequence[0]
    modifiers, key_text = _sequence_parts(combo)
    if not modifiers or not key_text:
        return None
    parts = [*modifiers, key_text]
    return "+".join(parts)


def _sequence_parts(combo: int) -> tuple[list[str], str]:
    all_modifiers = (
        int(Qt.KeyboardModifier.ShiftModifier)
        | int(Qt.KeyboardModifier.ControlModifier)
        | int(Qt.KeyboardModifier.AltModifier)
        | int(Qt.KeyboardModifier.MetaModifier)
    )
    key_int = combo & ~all_modifiers
    modifier_bits = combo & all_modifiers
    modifiers: list[str] = []
    for flag, name in (
        (int(Qt.KeyboardModifier.ShiftModifier), "Shift"),
        (int(Qt.KeyboardModifier.ControlModifier), "Ctrl"),
        (int(Qt.KeyboardModifier.AltModifier), "Alt"),
        (int(Qt.KeyboardModifier.MetaModifier), "Meta"),
    ):
        if modifier_bits & flag:
            modifiers.append(name)
    key_text = QKeySequence(key_int).toString(QKeySequence.SequenceFormat.PortableText)
    return modifiers, key_text
