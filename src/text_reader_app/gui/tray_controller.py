"""Tray controller for the initial TextReader GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from text_reader_app.hotkeys import format_hotkey_trigger

from .preferences_options import (
    SYNTHESIS_MODE_OPTIONS,
    build_menu_options,
    format_preference_label,
    synthesis_mode_label,
)
from .player_window import PlayerWindow

ActionCallback = Callable[[], None]
ValueCallback = Callable[[str], None]


@dataclass(slots=True)
class TrayActionCallbacks:
    """Callbacks that can be wired to application services later."""

    on_read_selection: ActionCallback | None = None
    on_read_clipboard: ActionCallback | None = None
    on_reader_changed: ValueCallback | None = None
    on_language_changed: ValueCallback | None = None
    on_synthesis_mode_changed: ValueCallback | None = None
    on_open_settings: ActionCallback | None = None
    on_change_hotkey: ActionCallback | None = None
    on_quit: ActionCallback | None = None


class TrayController:
    """Owns the tray icon, tray menu, and player window shell."""

    def __init__(
        self,
        app: QApplication,
        player_window: PlayerWindow | None = None,
        callbacks: TrayActionCallbacks | None = None,
        initial_hotkey_trigger: str = "Alt+L",
        initial_reader: str = "serena",
        initial_language: str = "german",
        initial_synthesis_mode: str = "whole",
        reader_options: tuple[str, ...] = (),
        language_options: tuple[str, ...] = (),
    ) -> None:
        self._app = app
        self._player_window = player_window or PlayerWindow()
        self._callbacks = callbacks or TrayActionCallbacks()
        self._tray_icon = QSystemTrayIcon(self._resolve_icon(), self._app)
        self._tray_menu = QMenu()
        self._hotkey_trigger = format_hotkey_trigger(initial_hotkey_trigger)
        self._reader_options = tuple(reader_options)
        self._language_options = tuple(language_options)
        self._active_reader = initial_reader.strip() or "serena"
        self._active_language = initial_language.strip() or "german"
        self._active_synthesis_mode = _normalize_synthesis_mode(initial_synthesis_mode)
        self._hotkey_info_action: QAction | None = None
        self._reader_actions = QActionGroup(self._tray_menu)
        self._reader_actions.setExclusive(True)
        self._language_actions = QActionGroup(self._tray_menu)
        self._language_actions.setExclusive(True)
        self._synthesis_mode_actions = QActionGroup(self._tray_menu)
        self._synthesis_mode_actions.setExclusive(True)
        self._reader_action_map: dict[str, QAction] = {}
        self._language_action_map: dict[str, QAction] = {}
        self._synthesis_mode_action_map: dict[str, QAction] = {}
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

    def show_settings(self) -> None:
        if self._callbacks.on_open_settings is None:
            return
        self._callbacks.on_open_settings()

    def change_hotkey(self) -> None:
        if self._callbacks.on_change_hotkey is None:
            return
        self._callbacks.on_change_hotkey()

    def set_callbacks(self, callbacks: TrayActionCallbacks) -> None:
        """Replace the tray callback bundle after construction."""

        self._callbacks = callbacks

    def set_hotkey_trigger(self, trigger: str) -> None:
        self._hotkey_trigger = format_hotkey_trigger(trigger)
        if self._hotkey_info_action is not None:
            self._hotkey_info_action.setText(f"Current hotkey: {self._hotkey_trigger}")
        self._tray_icon.setToolTip(_build_tray_tooltip(self._hotkey_trigger))

    def set_reader(self, reader: str) -> None:
        self._active_reader = reader.strip() or self._active_reader
        self._refresh_option_menu(
            option_type="reader",
            active_value=self._active_reader,
            option_values=self._reader_options,
        )

    def set_language(self, language: str) -> None:
        self._active_language = language.strip() or self._active_language
        self._refresh_option_menu(
            option_type="language",
            active_value=self._active_language,
            option_values=self._language_options,
        )

    def set_synthesis_mode(self, synthesis_mode: str) -> None:
        self._active_synthesis_mode = _normalize_synthesis_mode(synthesis_mode)
        self._refresh_option_menu(
            option_type="synthesis_mode",
            active_value=self._active_synthesis_mode,
            option_values=_synthesis_mode_values(),
        )

    def _configure_tray(self) -> None:
        self._tray_icon.setToolTip(_build_tray_tooltip(self._hotkey_trigger))
        self._tray_icon.activated.connect(self._handle_activation)

        # Window actions
        self._add_action("Open player", self.show_player)
        self._add_action("Open settings", self.show_settings)
        self._tray_menu.addSeparator()

        # Direct read actions
        self._add_action("Read selection", self._run_selection_action)
        self._add_action("Read clipboard", self._run_clipboard_action)
        self._tray_menu.addSeparator()

        # TTS preferences
        self._add_reader_menu()
        self._add_language_menu()
        self._add_synthesis_mode_menu()
        self._tray_menu.addSeparator()

        # Hotkey controls
        self._add_hotkey_actions()
        self._tray_menu.addSeparator()

        # Exit
        self._add_action("Quit", self._quit)
        self._tray_icon.setContextMenu(self._tray_menu)

    def _add_action(self, label: str, callback: ActionCallback) -> None:
        action = QAction(label, self._tray_menu)
        action.triggered.connect(callback)
        self._tray_menu.addAction(action)

    def _resolve_icon(self) -> QIcon:
        from .style_loader import load_app_icon
        icon = load_app_icon()
        if not icon.isNull():
            return icon
        return self._app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)

    def _add_hotkey_actions(self) -> None:
        self._hotkey_info_action = QAction(
            f"Current hotkey: {self._hotkey_trigger}",
            self._tray_menu,
        )
        self._hotkey_info_action.setEnabled(False)
        self._tray_menu.addAction(self._hotkey_info_action)
        self._add_action("Change hotkey…", self.change_hotkey)

    def _add_reader_menu(self) -> None:
        self._build_option_menu(
            title="Reader",
            option_type="reader",
            active_value=self._active_reader,
            option_values=self._reader_options,
        )

    def _add_language_menu(self) -> None:
        self._build_option_menu(
            title="Language",
            option_type="language",
            active_value=self._active_language,
            option_values=self._language_options,
        )

    def _add_synthesis_mode_menu(self) -> None:
        self._build_option_menu(
            title="Synthesis mode",
            option_type="synthesis_mode",
            active_value=self._active_synthesis_mode,
            option_values=_synthesis_mode_values(),
        )

    def _build_option_menu(
        self,
        *,
        title: str,
        option_type: str,
        active_value: str,
        option_values: tuple[str, ...],
    ) -> None:
        menu = self._tray_menu.addMenu(title)
        action_group = self._action_group_for(option_type)
        action_map = self._action_map_for(option_type)
        self._add_option_actions(
            menu=menu,
            action_group=action_group,
            action_map=action_map,
            option_type=option_type,
            active_value=active_value,
            option_values=option_values,
        )

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

    def _select_option(self, option_type: str, value: str) -> None:
        if option_type == "reader":
            self._active_reader = value
            if self._callbacks.on_reader_changed is not None:
                self._callbacks.on_reader_changed(value)
            return
        if option_type == "language":
            self._active_language = value
            if self._callbacks.on_language_changed is not None:
                self._callbacks.on_language_changed(value)
            return
        self._active_synthesis_mode = _normalize_synthesis_mode(value)
        if self._callbacks.on_synthesis_mode_changed is not None:
            self._callbacks.on_synthesis_mode_changed(self._active_synthesis_mode)

    def _refresh_option_menu(
        self,
        *,
        option_type: str,
        active_value: str,
        option_values: tuple[str, ...],
    ) -> None:
        action_map = self._action_map_for(option_type)
        if active_value not in action_map:
            self._rebuild_option_menu(
                option_type=option_type,
                active_value=active_value,
                option_values=option_values,
            )
            return
        action_map[active_value].setChecked(True)

    def _rebuild_option_menu(
        self,
        *,
        option_type: str,
        active_value: str,
        option_values: tuple[str, ...],
    ) -> None:
        menu_title = _option_menu_title(option_type)
        menu = self._find_submenu(menu_title)
        if menu is None:
            return
        menu.clear()
        action_map = self._action_map_for(option_type)
        action_map.clear()
        action_group = self._action_group_for(option_type)
        for action in list(action_group.actions()):
            action_group.removeAction(action)
        self._add_option_actions(
            menu=menu,
            action_group=action_group,
            action_map=action_map,
            option_type=option_type,
            active_value=active_value,
            option_values=option_values,
        )

    def _find_submenu(self, title: str) -> QMenu | None:
        for action in self._tray_menu.actions():
            menu = action.menu()
            if menu is not None and action.text() == title:
                return menu
        return None

    def _add_option_actions(
        self,
        *,
        menu: QMenu,
        action_group: QActionGroup,
        action_map: dict[str, QAction],
        option_type: str,
        active_value: str,
        option_values: tuple[str, ...],
    ) -> None:
        for value in build_menu_options(active_value, option_values):
            action = QAction(_option_label(option_type, value), menu)
            action.setCheckable(True)
            action.setChecked(value == active_value)
            action.triggered.connect(
                lambda checked=False, selected_value=value: self._select_option(
                    option_type,
                    selected_value,
                ),
            )
            action_group.addAction(action)
            action_map[value] = action
            menu.addAction(action)

    def _action_group_for(self, option_type: str) -> QActionGroup:
        if option_type == "reader":
            return self._reader_actions
        if option_type == "language":
            return self._language_actions
        return self._synthesis_mode_actions

    def _action_map_for(self, option_type: str) -> dict[str, QAction]:
        if option_type == "reader":
            return self._reader_action_map
        if option_type == "language":
            return self._language_action_map
        return self._synthesis_mode_action_map

    def _quit(self) -> None:
        if self._callbacks.on_quit is not None:
            self._callbacks.on_quit()
            return
        self._app.quit()


def _build_tray_tooltip(hotkey_trigger: str) -> str:
    return f"TextReader | Hotkey: {hotkey_trigger}"


def _normalize_synthesis_mode(mode: str) -> str:
    if mode == "streaming":
        return mode
    return "whole"


def _synthesis_mode_values() -> tuple[str, ...]:
    return tuple(value for value, _label in SYNTHESIS_MODE_OPTIONS)


def _option_menu_title(option_type: str) -> str:
    if option_type == "reader":
        return "Reader"
    if option_type == "language":
        return "Language"
    return "Synthesis mode"


def _option_label(option_type: str, value: str) -> str:
    if option_type == "synthesis_mode":
        return synthesis_mode_label(value)
    return format_preference_label(value)
