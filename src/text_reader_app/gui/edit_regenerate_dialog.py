"""Dialog for editing one history entry before regenerating audio."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from text_reader_app.domain.models import EntryRegenerationRequest

from .preferences_options import LANGUAGE_OPTIONS, READER_OPTIONS, SYNTHESIS_MODE_OPTIONS
from .style_loader import load_app_icon


class EditRegenerateDialog(QDialog):
    """Collect text and voice options for regenerating one entry."""

    def __init__(
        self,
        initial_request: EntryRegenerationRequest,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text_edit = QTextEdit()
        self._reader_box = QComboBox()
        self._language_box = QComboBox()
        self._synthesis_mode_box = QComboBox()
        self._save_as_new_entry_box = QCheckBox("Save as new entry")
        self._build_dialog()
        self._set_initial_request(initial_request)

    def request(self) -> EntryRegenerationRequest:
        """Return the current dialog state."""

        return EntryRegenerationRequest(
            text=self._text_edit.toPlainText().strip(),
            voice=self._reader_box.currentText().strip() or "serena",
            language=self._language_box.currentText().strip() or "german",
            synthesis_mode=self._synthesis_mode_box.currentData() or "whole",
            save_as_new_entry=self._save_as_new_entry_box.isChecked(),
        )

    def _build_dialog(self) -> None:
        self.setWindowTitle("Edit & regenerate")
        self.setWindowIcon(load_app_icon())
        self.resize(520, 360)
        self._configure_controls()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Text", self._text_edit)
        form.addRow("Reader", self._reader_box)
        form.addRow("Language", self._language_box)
        form.addRow("Synthesis", self._synthesis_mode_box)
        layout.addLayout(form)
        layout.addWidget(self._save_as_new_entry_box)
        layout.addWidget(self._build_button_box())

    def _configure_controls(self) -> None:
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setPlaceholderText("Edit text before regenerating audio.")
        self._reader_box.addItems(list(READER_OPTIONS))
        self._reader_box.setEditable(True)
        self._language_box.addItems(list(LANGUAGE_OPTIONS))
        self._language_box.setEditable(True)
        for value, label in SYNTHESIS_MODE_OPTIONS:
            self._synthesis_mode_box.addItem(label, value)

    def _set_initial_request(self, request: EntryRegenerationRequest) -> None:
        self._text_edit.setPlainText(request.text)
        self._select_editable_text(self._reader_box, request.voice)
        self._select_editable_text(self._language_box, request.language)
        self._select_synthesis_mode(request.synthesis_mode)
        self._save_as_new_entry_box.setChecked(request.save_as_new_entry)

    def _build_button_box(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Regenerate")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def _select_editable_text(self, combo_box: QComboBox, value: str) -> None:
        index = combo_box.findText(value)
        if index >= 0:
            combo_box.setCurrentIndex(index)
            return
        combo_box.setEditText(value)

    def _select_synthesis_mode(self, synthesis_mode: str) -> None:
        normalized = "streaming" if synthesis_mode == "streaming" else "whole"
        index = self._synthesis_mode_box.findData(normalized)
        self._synthesis_mode_box.setCurrentIndex(max(index, 0))


def show_edit_regenerate_dialog(
    *,
    parent: QWidget | None,
    initial_request: EntryRegenerationRequest,
) -> EntryRegenerationRequest | None:
    """Open the edit dialog and return the accepted request."""

    dialog = EditRegenerateDialog(initial_request=initial_request, parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    request = dialog.request()
    if not request.text:
        return None
    return request
