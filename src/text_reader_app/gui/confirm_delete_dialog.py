"""Styled confirmation dialog for destructive history actions."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDialog,
)

from .style_loader import load_app_icon


class ConfirmDeleteDialog(QDialog):
    """Small confirmation dialog styled like the main application."""

    def __init__(
        self,
        *,
        title: str,
        message: str,
        confirm_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._message_label = QLabel(message)
        self._cancel_button = QPushButton("Cancel")
        self._confirm_button = QPushButton(confirm_label)
        self._build_dialog(title)

    def _build_dialog(self, title: str) -> None:
        self.setWindowTitle(title)
        self.setWindowIcon(load_app_icon())
        self.resize(420, 170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(self._build_panel(), 1)
        layout.addLayout(self._build_button_row())

    def _build_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("dialogPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        self._message_label.setWordWrap(True)
        self._message_label.setObjectName("dialogMessageLabel")
        layout.addWidget(self._message_label)
        return frame

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        self._cancel_button.clicked.connect(self.reject)
        self._confirm_button.setObjectName("primaryButton")
        self._confirm_button.clicked.connect(self.accept)
        row.addWidget(self._cancel_button)
        row.addWidget(self._confirm_button)
        return row


def confirm_delete(
    *,
    parent: QWidget | None,
    title: str,
    message: str,
    confirm_label: str = "Delete",
) -> bool:
    """Return whether the destructive action was confirmed."""

    dialog = ConfirmDeleteDialog(
        title=title,
        message=message,
        confirm_label=confirm_label,
        parent=parent,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted
