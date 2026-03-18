"""Tray controller for the initial TextReader GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from .player_window import PlayerWindow

ActionCallback = Callable[[], None]
ModeCallback = Callable[[str], None]


@dataclass(slots=True)
class TrayActionCallbacks:
    """Callbacks that can be wired to application services later."""

    on_read_selection: ActionCallback | None = None
    on_read_clipboard: ActionCallback | None = None
    on_capture_mode_changed: ModeCallback | None = None
    on_quit: ActionCallback | None = None


class TrayController:
    """Owns the tray icon, tray menu, and player window shell."""

    def __init__(
        self,
        app: QApplication,
        player_window: PlayerWindow | None = None,
        callbacks: TrayActionCallbacks | None = None,
        initial_capture_mode: str = "selection",
    ) -> None:
        self._app = app
        self._player_window = player_window or PlayerWindow()
        self._callbacks = callbacks or TrayActionCallbacks()
        self._tray_icon = QSystemTrayIcon(self._resolve_icon(), self._app)
        self._tray_menu = QMenu()
        self._capture_mode_actions = QActionGroup(self._tray_menu)
        self._capture_mode_actions.setExclusive(True)
        self._selection_mode_action: QAction | None = None
        self._clipboard_mode_action: QAction | None = None
        self._active_capture_mode = _normalize_capture_mode(initial_capture_mode)
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

    def active_capture_mode(self) -> str:
        return self._active_capture_mode

    def set_active_capture_mode(self, mode: str) -> None:
        self._set_active_capture_mode(mode, notify=True)

    def _set_active_capture_mode(self, mode: str, notify: bool) -> None:
        normalized_mode = _normalize_capture_mode(mode)
        self._active_capture_mode = normalized_mode
        if self._selection_mode_action is not None:
            self._selection_mode_action.setChecked(normalized_mode == "selection")
        if self._clipboard_mode_action is not None:
            self._clipboard_mode_action.setChecked(normalized_mode == "clipboard")
        if notify and self._callbacks.on_capture_mode_changed is not None:
            self._callbacks.on_capture_mode_changed(normalized_mode)

    def _configure_tray(self) -> None:
        self._tray_icon.setToolTip("TextReader")
        self._tray_icon.activated.connect(self._handle_activation)
        self._add_action("Open player", self.show_player)
        self._add_action("Read active source", self._run_active_capture_action)
        self._add_capture_mode_menu()
        self._tray_menu.addSeparator()
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

    def _add_capture_mode_menu(self) -> None:
        mode_menu = self._tray_menu.addMenu("Active capture mode")
        self._selection_mode_action = self._build_mode_action("Selection", "selection")
        self._clipboard_mode_action = self._build_mode_action("Clipboard", "clipboard")
        mode_menu.addAction(self._selection_mode_action)
        mode_menu.addAction(self._clipboard_mode_action)
        self._set_active_capture_mode(self._active_capture_mode, notify=False)

    def _build_mode_action(self, label: str, mode: str) -> QAction:
        action = QAction(label, self._tray_menu)
        action.setCheckable(True)
        self._capture_mode_actions.addAction(action)
        action.triggered.connect(lambda checked=False, selected_mode=mode: self._select_mode(selected_mode))
        return action

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_player()

    def _run_active_capture_action(self) -> None:
        if self._active_capture_mode == "clipboard":
            self._run_clipboard_action()
            return
        self._run_selection_action()

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

    def _select_mode(self, mode: str) -> None:
        self.set_active_capture_mode(mode)

    def _quit(self) -> None:
        if self._callbacks.on_quit is not None:
            self._callbacks.on_quit()
            return
        self._app.quit()


def _normalize_capture_mode(mode: str) -> str:
    if mode == "clipboard":
        return mode
    return "selection"
