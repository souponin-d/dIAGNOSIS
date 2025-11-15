"""Toolbar widget for the main window."""

from __future__ import annotations

from PySide6.QtWidgets import QToolBar


class MainToolbar(QToolBar):
    """A minimal toolbar with placeholder actions."""

    def __init__(self, parent=None) -> None:
        super().__init__("Главное меню", parent)
        self._init_actions()

    def _init_actions(self) -> None:
        settings_action = self.addAction("Настройки")
        about_action = self.addAction("О программе")
        settings_action.triggered.connect(self._show_placeholder)
        about_action.triggered.connect(self._show_placeholder)

    def _show_placeholder(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "В разработке", "Функция пока не реализована.")
