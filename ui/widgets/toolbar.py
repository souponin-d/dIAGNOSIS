"""Toolbar widget for the main window."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QToolBar


class MainToolbar(QToolBar):
    """A minimal toolbar with placeholder actions."""

    settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Главное меню", parent)
        self._init_actions()

    def _init_actions(self) -> None:
        settings_action = self.addAction("Настройки")
        about_action = self.addAction("О программе")
        settings_action.triggered.connect(self.settings_requested.emit)
        about_action.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        QMessageBox.information(self, "О программе", "dIAGNOSIS V1 — прототип приложения.")
