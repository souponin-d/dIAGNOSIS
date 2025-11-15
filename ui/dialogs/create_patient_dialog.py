"""Dialog for creating a new patient entry."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class CreatePatientDialog(QDialog):
    """Modal dialog providing input fields for patient data."""

    _FIELD_LABELS = [
        "Возраст пациента",
        "Пол пациента",
        "Менопаузальный статус",
        "Статус рецепторов эстрогена",
        "Статус рецепторов прогестерона",
        "Статус HER2",
        "Мутация в генах BRCA1/2",
        "Уровень Ki-67 (%)",
        "Размер опухоли до лечения (см)",
        "Гистологическая градация опухоли (1-3)",
        "TMN",
        "E-кадгерин",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создание пациента")
        self.setModal(True)

        self._inputs: Dict[str, QLineEdit] = {}
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_animation.setDuration(1000)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self._build_layout()

    def _build_layout(self) -> None:
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(12)

        for index, label_text in enumerate(self._FIELD_LABELS):
            row = index % 6
            column = (index // 6) * 2

            label = QLabel(label_text, self)
            input_field = QLineEdit(self)
            input_field.setMaximumWidth(220)

            grid_layout.addWidget(label, row, column)
            grid_layout.addWidget(input_field, row, column + 1)

            self._inputs[label_text] = input_field

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        import_button = QPushButton("Импорт из ЕМИАС", self)
        create_button = QPushButton("Создать", self)
        create_button.clicked.connect(self.accept)

        buttons_layout.addWidget(import_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(create_button)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_layout.addLayout(grid_layout)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        self.setFixedWidth(700)
        self.setSizeGripEnabled(False)

    def collected_data(self) -> Dict[str, str]:
        """Return the current values from the input fields."""

        return {label: field.text() for label, field in self._inputs.items()}

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._opacity_effect.setOpacity(0.0)
        self._fade_animation.stop()
        self._fade_animation.start()
        super().showEvent(event)
