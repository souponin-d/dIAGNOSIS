"""Dialog for creating a new patient entry."""

from __future__ import annotations

from typing import Dict, List

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CreatePatientDialog(QDialog):
    """Modal dialog providing input fields for patient data."""

    _FIELD_LABELS = [
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

        self._inputs: Dict[str, QWidget] = {}
        self._field_order: List[str] = []

        self._build_layout()

    def _build_layout(self) -> None:
        header_label = QLabel("Добавление нового пациента", self)
        header_label.setStyleSheet("font-size: 20px; font-weight: 600;")

        identity_layout = QGridLayout()
        identity_layout.setHorizontalSpacing(20)
        identity_layout.setVerticalSpacing(12)
        for column in range(3):
            identity_layout.setColumnStretch(column, 1)

        self._add_field(identity_layout, "Фамилия", QLineEdit(self), 0, 0)
        self._add_field(identity_layout, "Имя", QLineEdit(self), 0, 1)
        self._add_field(identity_layout, "Отчество", QLineEdit(self), 0, 2)

        age_input = QSpinBox(self)
        age_input.setRange(0, 120)
        self._add_field(identity_layout, "Возраст пациента", age_input, 1, 0)

        sex_input = QComboBox(self)
        sex_input.addItems(["М", "Ж"])
        self._add_field(identity_layout, "Пол пациента", sex_input, 1, 1)

        menopause_input = QLineEdit(self)
        self._add_field(identity_layout, "Менопаузальный статус", menopause_input, 1, 2)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

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

            self._register_input(label_text, input_field)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        import_button = QPushButton("Импорт из ЕМИАС", self)
        import_button.setEnabled(False)
        create_button = QPushButton("Создать", self)
        create_button.clicked.connect(self.accept)

        buttons_layout.addWidget(import_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(create_button)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_layout.addWidget(header_label)
        main_layout.addLayout(identity_layout)
        main_layout.addWidget(separator)
        main_layout.addLayout(grid_layout)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        self.setFixedWidth(700)
        self.setSizeGripEnabled(False)

    def collected_data(self) -> Dict[str, str]:
        """Return the current values from the input fields."""

        return {
            label: self._read_value(self._inputs[label])
            for label in self._field_order
        }

    def _register_input(self, label: str, widget: QWidget) -> None:
        self._inputs[label] = widget
        self._field_order.append(label)

    def _add_field(
        self,
        layout: QGridLayout,
        label_text: str,
        widget: QWidget,
        row: int,
        column: int,
    ) -> None:
        container = QWidget(self)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        label = QLabel(label_text, self)
        container_layout.addWidget(label)
        container_layout.addWidget(widget)

        container.setLayout(container_layout)
        layout.addWidget(container, row, column)
        self._register_input(label_text, widget)

    def _read_value(self, widget: QWidget) -> str:
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QSpinBox):
            return str(widget.value())
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""
