"""Application settings dialog placeholder."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from config import AppConfig


class SettingsDialog(QDialog):
    """Allow switching between local and HTTP analysis modes."""

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")

        self._mode_selector = QComboBox(self)
        self._mode_selector.addItems(["local", "http"])
        self._mode_selector.setCurrentText(config.analysis_mode)

        self._backend_url = QLineEdit(config.backend_base_url, self)

        form_layout = QFormLayout()
        form_layout.addRow("Режим анализа", self._mode_selector)
        form_layout.addRow("URL backend", self._backend_url)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_mode(self) -> str:
        """Return the chosen analysis mode."""

        return self._mode_selector.currentText()

    def backend_url(self) -> str:
        """Return the configured backend URL."""

        return self._backend_url.text()
