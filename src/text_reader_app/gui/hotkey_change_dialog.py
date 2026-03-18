"""Dialog for capturing a new hotkey combination from the user."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QKeySequenceEdit,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from text_reader_app.hotkeys import format_hotkey_trigger


def show_hotkey_dialog(
    parent: QWidget | None = None,
    current_trigger: str = "Alt+L",
) -> str | None:
    """Capture one hotkey combination and return it as ``Alt+L`` style text."""

    dialog = QDialog(parent)
    dialog.setWindowTitle("Change Hotkey")
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Enter a new hotkey:"))
    sequence_edit = QKeySequenceEdit(dialog)
    sequence_edit.setKeySequence(QKeySequence(current_trigger))
    layout.addWidget(sequence_edit)
    hint = QLabel("Allowed: Alt, Ctrl, Shift, Meta plus one key.")
    hint.setWordWrap(True)
    hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(hint)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    trigger = _trigger_from_sequence(sequence_edit.keySequence())
    if trigger is None:
        return None
    return format_hotkey_trigger(trigger)


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
