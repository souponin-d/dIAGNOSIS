"""Patient data entry form."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PatientForm(QWidget):
    """Widget used to collect minimal patient data."""

    analyze_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._age_input = QSpinBox(self)
        self._age_input.setRange(0, 120)
        self._sex_input = QComboBox(self)
        self._sex_input.addItems(["Мужской", "Женский", "Не указан"])
        self._notes_input = QLineEdit(self)

        form_layout = QFormLayout()
        form_layout.addRow("Возраст", self._age_input)
        form_layout.addRow("Пол", self._sex_input)
        form_layout.addRow("Примечание", self._notes_input)

        self._analyze_button = QPushButton("Проанализировать", self)
        self._analyze_button.clicked.connect(self._on_analyze_clicked)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self._analyze_button)
        layout.addStretch()
        self.setLayout(layout)

    def _on_analyze_clicked(self) -> None:
        payload: Dict[str, object] = {
            "age": self._age_input.value(),
            "sex": self._sex_input.currentText(),
            "lab_results": {"note_length": len(self._notes_input.text())},
        }
        self.analyze_requested.emit(payload)
