"""Dialog for editing one history entry before regenerating audio."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QFormLayout,
    QTextEdit,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from text_reader_app.domain.models import EntryRegenerationRequest

from .preferences_options import (
    LANGUAGE_OPTIONS,
    READER_OPTIONS,
    SYNTHESIS_MODE_OPTIONS,
    reader_info_text,
)
from .style_loader import load_app_icon


def _show_info_popup(button: QToolButton) -> None:
    """Show the button's tooltip as a click-triggered popup."""
    tip = button.toolTip()
    if tip:
        QToolTip.showText(button.mapToGlobal(QPoint(0, button.height())), tip, button)


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
        self._reader_info_button = QToolButton()
        self._language_box = QComboBox()
        self._synthesis_mode_box = QComboBox()
        self._save_as_new_entry_box = QCheckBox("Save as new entry")
        self._cancel_button = QPushButton("Cancel")
        self._regenerate_button = QPushButton("Regenerate")
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
        self.resize(560, 420)
        self._configure_controls()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(self._build_panel(), 1)
        layout.addLayout(self._build_button_row())

    def _build_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("dialogPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Text", self._build_text_row())
        form.addRow("Reader", self._build_reader_row())
        form.addRow("Language", self._language_box)
        form.addRow("Synthesis", self._synthesis_mode_box)
        layout.addLayout(form)
        layout.addWidget(self._save_as_new_entry_box)
        return frame

    def _configure_controls(self) -> None:
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setObjectName("dialogTextEdit")
        self._text_edit.setPlaceholderText("Edit text before regenerating audio.")
        self._reader_box.addItems(list(READER_OPTIONS))
        self._reader_box.setEditable(True)
        self._reader_info_button.setText("i")
        self._reader_info_button.setObjectName("infoButton")
        self._reader_info_button.setToolTip("Reader info")
        self._reader_info_button.setAutoRaise(True)
        self._reader_info_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reader_info_button.clicked.connect(
            lambda: _show_info_popup(self._reader_info_button),
        )
        self._reader_box.currentTextChanged.connect(self._update_reader_info)
        self._language_box.addItems(list(LANGUAGE_OPTIONS))
        self._language_box.setEditable(True)
        for value, label in SYNTHESIS_MODE_OPTIONS:
            self._synthesis_mode_box.addItem(label, value)

    def _build_text_row(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("formRow")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self._text_edit, 1)
        # Invisible spacer matching info button width so text edit aligns with combos
        spacer = QWidget()
        spacer.setObjectName("formRow")
        spacer.setFixedWidth(20)
        row.addWidget(spacer)
        return container

    def _build_reader_row(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("formRow")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self._reader_box, 1)
        row.addWidget(self._reader_info_button)
        return container

    def _update_reader_info(self, reader: str) -> None:
        info_text = reader_info_text(reader)
        self._reader_box.setToolTip(info_text)
        self._reader_info_button.setToolTip(info_text or "Reader info")

    def _set_initial_request(self, request: EntryRegenerationRequest) -> None:
        self._text_edit.setPlainText(request.text)
        self._select_editable_text(self._reader_box, request.voice)
        self._update_reader_info(request.voice)
        self._select_editable_text(self._language_box, request.language)
        self._select_synthesis_mode(request.synthesis_mode)
        self._save_as_new_entry_box.setChecked(request.save_as_new_entry)

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        self._cancel_button.clicked.connect(self.reject)
        self._regenerate_button.setObjectName("primaryButton")
        self._regenerate_button.clicked.connect(self.accept)
        row.addWidget(self._cancel_button)
        row.addWidget(self._regenerate_button)
        return row

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
