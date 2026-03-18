"""Tray controller for the initial TextReader GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from .player_window import PlayerWindow

ActionCallback = Callable[[], None]


@dataclass(slots=True)
class TrayActionCallbacks:
    """Callbacks that can be wired to application services later."""

    on_read_selection: ActionCallback | None = None
    on_read_clipboard: ActionCallback | None = None
    on_quit: ActionCallback | None = None


class TrayController:
    """Owns the tray icon, tray menu, and player window shell."""

    def __init__(
        self,
        app: QApplication,
        player_window: PlayerWindow | None = None,
        callbacks: TrayActionCallbacks | None = None,
    ) -> None:
        self._app = app
        self._player_window = player_window or PlayerWindow()
        self._callbacks = callbacks or TrayActionCallbacks()
        self._tray_icon = QSystemTrayIcon(self._resolve_icon(), self._app)
        self._tray_menu = QMenu()
        self._configure_tray()

    def show(self) -> None:
        self._tray_icon.show()
        self._tray_icon.showMessage(
            "TextReader",
            "Tray shell started.",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )

    def show_player(self) -> None:
        self._player_window.show()
        self._player_window.raise_()
        self._player_window.activateWindow()

    def _configure_tray(self) -> None:
        self._tray_icon.setToolTip("TextReader")
        self._tray_icon.activated.connect(self._handle_activation)
        self._add_action("Open player", self.show_player)
        self._add_action("Read selection", self._run_selection_action)
        self._add_action("Read clipboard", self._run_clipboard_action)
        self._tray_menu.addSeparator()
        self._add_action("Quit", self._quit)
        self._tray_icon.setContextMenu(self._tray_menu)

    def _add_action(self, label: str, callback: ActionCallback) -> None:
        action = QAction(label, self._tray_menu)
        action.triggered.connect(callback)
        self._tray_menu.addAction(action)

    def _resolve_icon(self) -> QIcon:
        icon = self._app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        if not icon.isNull():
            return icon
        return QIcon()

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_player()

    def _run_selection_action(self) -> None:
        self._run_action(
            self._callbacks.on_read_selection,
            "Read selection is not wired yet.",
        )

    def _run_clipboard_action(self) -> None:
        self._run_action(
            self._callbacks.on_read_clipboard,
            "Read clipboard is not wired yet.",
        )

    def _run_action(self, callback: ActionCallback | None, placeholder_text: str) -> None:
        if callback is None:
            self._player_window.set_status_text("placeholder")
            self._player_window.set_preview_text(placeholder_text)
            self.show_player()
            return
        callback()

    def _quit(self) -> None:
        if self._callbacks.on_quit is not None:
            self._callbacks.on_quit()
            return
        self._app.quit()
