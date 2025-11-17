"""Dialog for creating a new patient entry."""

from __future__ import annotations

import csv
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Mapping

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator


class CreatePatientDialog(QDialog):
    """Modal dialog providing input fields for patient data."""

    _FIELD_LABELS = [
        "Статус:",
        "Рецептор эстрогена",
        "Рецептор прогестерона",
        "HER2",
        "Мутации в генах BRCA1/2",
        "E-кадгерин",
        "Уровень Ki-67 (%)",
        "Размер опухоли до лечения (см)",
        "Гистологическая градация опухоли (1-3)",
        "T",
        "M",
        "N",
    ]

    _REGRESSION_REQUIRED_FIELDS = (
        "Дата рождения",
        "Менопаузальный статус",
        "Рецептор эстрогена",
        "Рецептор прогестерона",
        "HER2",
        "Мутации в генах BRCA1/2",
        "Уровень Ki-67 (%)",
        "Размер опухоли до лечения (см)",
        "T",
        "M",
        "N",
    )

    _DATASET_PATH = (
        Path(__file__).resolve().parents[2]
        / "resources"
        / "datasets"
        / "breast_cancer_data.xlsx - Стадия 1.csv"
    )
    _DATASET_PATIENT_ID = "BC_1_0001"

    def __init__(
        self,
        parent=None,
        patient_data: Mapping[str, str] | None = None,
        *,
        is_edit: bool = False,
    ) -> None:
        super().__init__(parent)
        self._is_edit_mode = is_edit
        self._initial_data = dict(patient_data or {})

        self.setWindowTitle(
            "Редактирование пациента" if self._is_edit_mode else "Создание пациента"
        )
        self.setModal(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._apply_styles()

        self._inputs: Dict[str, QWidget] = {}
        self._field_order: List[str] = []

        self._build_layout()
        if self._initial_data:
            self._populate_initial_data(self._initial_data)

    def _build_layout(self) -> None:
        header_text = "Редактирование пациента" if self._is_edit_mode else "Добавление нового пациента"
        header_label = QLabel(header_text, self)
        header_label.setObjectName("dialogHeader")

        identity_layout = QGridLayout()
        identity_layout.setHorizontalSpacing(20)
        identity_layout.setVerticalSpacing(12)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        for column in range(3):
            identity_layout.setColumnStretch(column, 1)

        self._add_field(identity_layout, "Фамилия", QLineEdit(self), 0, 0)
        self._add_field(identity_layout, "Имя", QLineEdit(self), 0, 1)
        self._add_field(identity_layout, "Отчество", QLineEdit(self), 0, 2)

        birth_date_container = self._create_birth_date_field()
        identity_layout.addWidget(birth_date_container, 1, 0)

        sex_input = QComboBox(self)
        sex_input.addItems(["Ж", "М"])
        sex_input.setCurrentText("Ж")
        self._add_field(identity_layout, "Пол пациента", sex_input, 1, 1)
        self._sex_input = sex_input

        menopause_input = MenopauseStatusField(self)
        self._menopause_container = self._add_field(
            identity_layout,
            "Менопаузальный статус",
            menopause_input,
            1,
            2,
        )
        self._menopause_field = menopause_input
        self._sex_input.currentTextChanged.connect(self._on_sex_changed)
        self._on_sex_changed(self._sex_input.currentText())

        separator = QFrame(self)
        separator.setObjectName("lineSeparator")
        separator.setFrameShape(QFrame.NoFrame)

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(12)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        vertical_fields = {
            "Уровень Ki-67 (%)",
            "Размер опухоли до лечения (см)",
            "Гистологическая градация опухоли (1-3)",
        }

        for index, label_text in enumerate(self._FIELD_LABELS):
            row = index % 6
            column = (index // 6) * 2

            if label_text == "Статус:":
                section_label = QLabel(label_text, self)
                section_label.setStyleSheet("font-weight: 600;")
                grid_layout.addWidget(section_label, row, column, 1, 2)
                continue

            input_field = self._create_field_widget(label_text)

            if label_text in vertical_fields:
                container = QWidget(self)
                container_layout = QVBoxLayout()
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(6)
                container_layout.addWidget(QLabel(label_text, self))
                container_layout.addWidget(input_field)
                container.setLayout(container_layout)
                grid_layout.addWidget(container, row, column, 1, 2)
            else:
                label = QLabel(label_text, self)
                grid_layout.addWidget(label, row, column)
                grid_layout.addWidget(input_field, row, column + 1)

            self._register_input(label_text, input_field)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)

        import_button = QPushButton("Импорт из ЕМИАС", self)
        import_button.setEnabled(False)
        import_button.setObjectName("secondaryButton")

        dataset_button = QPushButton("Импорт из датасета", self)
        dataset_button.setObjectName("secondaryButton")
        dataset_button.clicked.connect(self._on_import_dataset_clicked)

        submit_label = "Сохранить" if self._is_edit_mode else "Создать"
        create_button = QPushButton(submit_label, self)
        create_button.clicked.connect(self._on_submit_clicked)

        for button in (import_button, dataset_button, create_button):
            button.setCursor(Qt.PointingHandCursor)

        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(dataset_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(create_button)

        content_card = QFrame(self)
        content_card.setObjectName("patientFormCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(24)
        card_layout.addWidget(header_label)
        card_layout.addLayout(identity_layout)
        card_layout.addWidget(separator)
        card_layout.addLayout(grid_layout)
        card_layout.addLayout(buttons_layout)
        content_card.setLayout(card_layout)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(content_card)

        self.setLayout(outer_layout)

        self.setFixedWidth(720)
        self.setSizeGripEnabled(False)

    def _on_submit_clicked(self) -> None:
        if not self._validate_required_fields():
            return
        self.accept()

    def _on_import_dataset_clicked(self) -> None:
        try:
            record = self._load_dataset_record(self._DATASET_PATIENT_ID)
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Датасет не найден",
                "Файл датасета отсутствует по ожидаемому пути."
            )
            return
        except Exception as error:  # pragma: no cover - user feedback branch
            QMessageBox.critical(
                self,
                "Ошибка чтения датасета",
                f"Не удалось обработать файл датасета: {error}",
            )
            return

        if not record:
            QMessageBox.warning(
                self,
                "Пациент не найден",
                "Пациент с указанным идентификатором отсутствует в датасете.",
            )
            return

        self._apply_dataset_record(record)
        self._clear_validation_errors()

    def _apply_styles(self) -> None:
        """Apply a lightweight stylesheet for the dialog."""

        self.setStyleSheet(
            """
            QDialog {
                background-color: #f2f4f7;
            }
            #patientFormCard {
                background-color: #ffffff;
                border-radius: 24px;
                border: 1px solid #e1e7ef;
            }
            #dialogHeader {
                font-size: 22px;
                font-weight: 600;
                color: #111827;
            }
            QLabel {
                color: #1f2937;
                font-size: 13px;
            }
            QLineEdit,
            QComboBox {
                border: 1px solid #d7dde7;
                border-radius: 10px;
                padding: 8px 12px;
                background-color: #ffffff;
            }
            QLineEdit[hasError="true"],
            QComboBox[hasError="true"] {
                border-color: #e53e3e;
                background-color: #fff5f5;
            }
            QLineEdit:focus,
            QComboBox:focus {
                border-color: #1f6feb;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #d7dde7;
                border-radius: 8px;
                background: #ffffff;
                selection-background-color: #163455;
                selection-color: #ffffff;
            }
            QRadioButton {
                spacing: 6px;
            }
            QPushButton {
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                background-color: #163455;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #cbd3df;
                color: #8d9aad;
            }
            QPushButton#secondaryButton {
                background-color: transparent;
                color: #163455;
                border: 1px solid #cbd3df;
            }
            QRadioButton[hasError="true"]::indicator {
                border: 2px solid #e53e3e;
            }
            #lineSeparator {
                background-color: #ecf0f7;
                min-height: 1px;
                max-height: 1px;
            }
            """
        )

    def collected_data(self) -> Dict[str, str]:
        """Return the current values from the input fields."""

        data: Dict[str, str] = {}
        for label in self._field_order:
            value = self._read_value(self._inputs[label])
            if isinstance(value, dict):
                data.update(value)
            else:
                data[label] = value
        return data

    def _populate_initial_data(self, data: Mapping[str, str]) -> None:
        for label, widget in self._inputs.items():
            if label not in data:
                continue
            value = data[label]
            if isinstance(widget, QLineEdit):
                widget.setText(value)
            elif isinstance(widget, QComboBox):
                index = widget.findText(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, MenopauseStatusField):
                widget.set_value(value)
            elif isinstance(widget, NClassificationField):
                widget.set_value(value)
            elif isinstance(widget, PositiveNegativeField):
                widget.set_value(value)

    def _validate_required_fields(self) -> bool:
        missing: list[str] = []
        for label in self._REGRESSION_REQUIRED_FIELDS:
            widget = self._inputs.get(label)
            if not widget:
                continue
            value = (self._read_value(widget) or "").strip()
            is_missing = False
            if label == "Дата рождения":
                is_missing = not value or "_" in value
            else:
                is_missing = not value

            self._set_widget_error_state(widget, is_missing)
            if is_missing:
                missing.append(label)

        if not missing:
            return True

        message = "\n".join(missing)
        QMessageBox.warning(
            self,
            "Недостаточно данных",
            "Для расчёта прогноза заполните поля:\n" + message,
        )
        first_missing = missing[0]
        widget = self._inputs.get(first_missing)
        if isinstance(widget, QLineEdit):
            widget.setFocus()
        return False

    def _clear_validation_errors(self) -> None:
        for label in self._REGRESSION_REQUIRED_FIELDS:
            widget = self._inputs.get(label)
            if widget:
                self._set_widget_error_state(widget, False)

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
    ) -> QWidget:
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
        return container

    def _create_birth_date_field(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel("Дата рождения", self)
        layout.addWidget(label)

        birth_layout = QHBoxLayout()
        birth_layout.setContentsMargins(0, 0, 0, 0)
        birth_layout.setSpacing(8)

        birth_input = QLineEdit(self)
        birth_input.setInputMask("00.00.0000;_")
        birth_input.setPlaceholderText("ДД.ММ.ГГГГ")
        birth_input.setMaximumWidth(130)

        age_display = QLineEdit(self)
        age_display.setReadOnly(True)
        age_display.setFocusPolicy(Qt.NoFocus)
        age_display.setPlaceholderText("Возраст")
        age_display.setMaximumWidth(130)

        birth_layout.addWidget(birth_input)
        birth_layout.addWidget(age_display)

        layout.addLayout(birth_layout)
        container.setLayout(layout)

        self._birth_date_input = birth_input
        self._age_display = age_display

        birth_input.textChanged.connect(self._on_birth_date_changed)

        self._register_input("Дата рождения", birth_input)
        return container

    def _on_birth_date_changed(self, text: str) -> None:
        if "_" in text:
            self._age_display.clear()
            return

        try:
            birth_date = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            self._age_display.clear()
            return

        years = self._calculate_age(birth_date)
        suffix = self._format_years(years)
        self._age_display.setText(f"{years} {suffix}")

    @staticmethod
    def _calculate_age(birth_date: date) -> int:
        today = date.today()
        years = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            years -= 1
        return max(0, years)

    @staticmethod
    def _format_years(years: int) -> str:
        if 11 <= years % 100 <= 14:
            return "лет"
        last_digit = years % 10
        if last_digit == 1:
            return "год"
        if 2 <= last_digit <= 4:
            return "года"
        return "лет"

    def _create_field_widget(self, label_text: str) -> QWidget:
        if label_text in {
            "Рецептор эстрогена",
            "Рецептор прогестерона",
            "HER2",
            "Мутации в генах BRCA1/2",
            "E-кадгерин",
        }:
            return PositiveNegativeField(self)
        if label_text == "T":
            return self._create_t_field()
        if label_text == "M":
            return self._create_m_field()
        if label_text == "N":
            return NClassificationField(self)

        input_field = QLineEdit(self)
        if label_text in {
            "Уровень Ki-67 (%)",
            "Размер опухоли до лечения (см)",
            "Гистологическая градация опухоли (1-3)",
        }:
            input_field.setMaximumWidth(320)
        else:
            input_field.setMaximumWidth(220)

        if label_text == "Уровень Ki-67 (%)":
            pattern = QRegularExpression(r"^$|^(?:100(?:[\.,]0{0,2})?|\d{1,2}(?:[\.,]\d{0,2})?)$")
            input_field.setValidator(QRegularExpressionValidator(pattern, input_field))
        elif label_text == "Размер опухоли до лечения (см)":
            pattern = QRegularExpression(r"^$|^(?:\d{1,2}(?:[\.,]\d{0,2})?)$")
            input_field.setValidator(QRegularExpressionValidator(pattern, input_field))
        elif label_text == "Гистологическая градация опухоли (1-3)":
            input_field.setValidator(QIntValidator(1, 3, input_field))
        return input_field

    def _create_t_field(self) -> QWidget:
        options = [
            "Tx — Недостаточно данных для оценки первичной опухоли.",
            "T0 — Первичная опухоль не обнаружена.",
            "Tis (DCIS) — Протоковая карцинома in situ (неинвазивный рак, ограничена протоками).",
            "Tis (Педжета) — Рак Педжета соска без признаков инвазивного рака или DCIS в паренхиме.",
            "T1 — Опухоль ≤ 20 мм:",
            "T1mic — Микроинвазия ≤ 1 мм.",
            "T1a — >1 мм, но ≤5 мм.",
            "T1b — >5 мм, но ≤10 мм.",
            "T1c — >10 мм, но ≤20 мм.",
            "T2 — Опухоль >20 мм, но ≤50 мм.",
            "T3 — Опухоль >50 мм.",
            "T4 — Опухоль любого размера с распространением на грудную стенку и/или кожу:",
            "T4a — Распространение на грудную стенку.",
            "T4b — Изъязвление кожи, узелки вокруг опухоли, отёк («апельсиновая корочка»), но не воспалительный рак.",
            "T4c — Сочетание T4a и T4b.",
            "T4d — Воспалительный рак.",
        ]
        combo = QComboBox(self)
        combo.addItems(options)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.view().setTextElideMode(Qt.ElideNone)
        combo.setMinimumWidth(360)
        return combo

    def _create_m_field(self) -> QWidget:
        options = [
            "cM — клиническая классификация (до операции)",
            "cM0 — Нет клинических или радиографических признаков отдалённых метастазов.",
            "cM0(i+) — Нет клинических или радиографических признаков отдалённых метастазов, но обнаружены опухолевые клетки или их комплексы размером не более 0,2 мм в крови, костном мозге или других не регионарных тканях при отсутствии симптомов.",
            "cM1 — Есть отдалённые метастазы, подтверждённые клинически или с помощью методов визуализации (например, КТ, ПЭТ, МРТ, сканирование костей)",
            "pM — патологическая классификация (после операции)",
            "pM1 — Любые гистологически доказанные отдалённые метастазы или метастазы более 0,2 мм в нерегионарных лимфоузлах.",
        ]
        combo = QComboBox(self)
        combo.addItems(options)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.view().setTextElideMode(Qt.ElideNone)
        combo.setMinimumWidth(360)
        return combo

    def _on_sex_changed(self, sex: str) -> None:
        self._menopause_field.set_sex(sex)
        if hasattr(self, "_menopause_container"):
            self._menopause_container.setVisible(sex == "Ж")

    def _read_value(self, widget: QWidget) -> str:
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, MenopauseStatusField):
            return widget.value()
        if isinstance(widget, NClassificationField):
            return widget.value()
        if isinstance(widget, PositiveNegativeField):
            return widget.value()
        return ""

    def _set_widget_error_state(self, widget: QWidget, has_error: bool) -> None:
        if hasattr(widget, "set_error_state"):
            try:
                widget.set_error_state(has_error)  # type: ignore[attr-defined]
            except TypeError:
                pass
            return
        if isinstance(widget, (QLineEdit, QComboBox)):
            widget.setProperty("hasError", has_error)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _load_dataset_record(self, patient_id: str) -> Mapping[str, str] | None:
        if not self._DATASET_PATH.exists():
            raise FileNotFoundError(self._DATASET_PATH)

        with self._DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if (row.get("patient_id") or "").strip() == patient_id:
                    return row
        return None

    def _apply_dataset_record(self, record: Mapping[str, str]) -> None:
        self._set_line_edit_value("Фамилия", record.get("patient_id", ""))
        self._set_line_edit_value("Имя", "Пациент")
        self._set_line_edit_value("Отчество", "")

        birth_date = self._derive_birth_date_from_age(record.get("age"))
        if birth_date:
            self._birth_date_input.setText(birth_date)

        gender = (record.get("gender") or "").strip()
        normalized_gender = gender.lower()
        mapped_gender = ""
        if normalized_gender in {"ж", "f", "female"}:
            mapped_gender = "Ж"
        elif normalized_gender in {"м", "m", "male"}:
            mapped_gender = "М"
        if mapped_gender:
            self._sex_input.setCurrentText(mapped_gender)

        menopause = record.get("menopausal_status", "")
        if isinstance(self._menopause_field, MenopauseStatusField):
            self._menopause_field.set_value(menopause)

        self._apply_marker_value("Рецептор эстрогена", record.get("er_status"))
        self._apply_marker_value("Рецептор прогестерона", record.get("pr_status"))
        self._apply_marker_value("HER2", record.get("her2_status"))
        self._apply_marker_value("Мутации в генах BRCA1/2", record.get("brca_mutation"))

        ki67_value = self._normalize_dataset_decimal(record.get("ki67_level"))
        if ki67_value is not None:
            self._set_line_edit_value("Уровень Ki-67 (%)", f"{ki67_value}")

        tumor_grade = record.get("tumor_grade", "")
        self._set_line_edit_value("Гистологическая градация опухоли (1-3)", tumor_grade or "")

        tumor_size = self._normalize_dataset_decimal(record.get("tumor_size_before"))
        if tumor_size is not None:
            self._set_line_edit_value("Размер опухоли до лечения (см)", f"{tumor_size}")

        self._apply_t_category(tumor_size)
        self._apply_m_category(record.get("has_metastasis"))
        self._apply_n_category(record)

    def _set_line_edit_value(self, label: str, value: str) -> None:
        widget = self._inputs.get(label)
        if isinstance(widget, QLineEdit):
            widget.setText(value)

    def _apply_marker_value(self, label: str, raw_value: str | None) -> None:
        widget = self._inputs.get(label)
        if not isinstance(widget, PositiveNegativeField):
            return
        widget.set_value(self._boolean_to_marker(raw_value))

    @staticmethod
    def _boolean_to_marker(value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"true", "1", "yes", "да", "+"}:
            return "+"
        if normalized in {"false", "0", "no", "нет", "-"}:
            return "-"
        return ""

    def _normalize_dataset_decimal(self, value: str | None) -> float | None:
        if not value:
            return None
        cleaned = value.replace("\"", "").replace(",", ".").strip()
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    def _derive_birth_date_from_age(self, age_value: str | None) -> str | None:
        if not age_value:
            return None
        try:
            years = int(float(age_value))
        except ValueError:
            return None
        today = date.today()
        birth_year = max(1900, today.year - years)
        birth_date = date(birth_year, 1, 1)
        return birth_date.strftime("%d.%m.%Y")

    def _apply_t_category(self, tumor_size: float | None) -> None:
        widget = self._inputs.get("T")
        if not isinstance(widget, QComboBox) or tumor_size is None:
            return

        selection = self._derive_t_category(tumor_size)
        if selection:
            self._select_combo_option(widget, selection)

    def _apply_m_category(self, has_metastasis: str | None) -> None:
        widget = self._inputs.get("M")
        if not isinstance(widget, QComboBox):
            return
        is_positive = (has_metastasis or "").strip().lower() in {"true", "1", "yes"}
        self._select_combo_option(widget, "cM1" if is_positive else "cM0")

    def _apply_n_category(self, record: Mapping[str, str]) -> None:
        widget = self._inputs.get("N")
        if not isinstance(widget, NClassificationField):
            return
        nodes_raw = record.get("positive_lymph_nodes", "0")
        try:
            nodes = int(float(nodes_raw))
        except ValueError:
            nodes = 0

        lymph_status = (record.get("lymph_node_status") or "").strip().lower()
        if nodes >= 10:
            prefix = "cN3"
        elif nodes >= 4:
            prefix = "cN2"
        elif nodes >= 1 or lymph_status in {"positive", "yes"}:
            prefix = "cN1"
        else:
            prefix = "cN0"

        widget.set_value(prefix)

    @staticmethod
    def _derive_t_category(size_cm: float | None) -> str | None:
        if size_cm is None:
            return None
        size_mm = size_cm * 10.0
        if size_mm <= 1:
            return "T1mic"
        if size_mm <= 5:
            return "T1a"
        if size_mm <= 10:
            return "T1b"
        if size_mm <= 20:
            return "T1c"
        if size_mm <= 50:
            return "T2"
        return "T3"

    @staticmethod
    def _select_combo_option(combo: QComboBox, prefix: str) -> None:
        index = combo.findText(prefix, Qt.MatchStartsWith)
        if index >= 0:
            combo.setCurrentIndex(index)


class PositiveNegativeField(QWidget):
    """Simple + / - selector represented by radio buttons."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._button_group = QButtonGroup(self)
        self._positive = QRadioButton("+", self)
        self._negative = QRadioButton("-", self)
        self._button_group.addButton(self._positive)
        self._button_group.addButton(self._negative)

        layout.addWidget(self._positive)
        layout.addWidget(self._negative)
        layout.addStretch(1)

        self.setLayout(layout)
        self._has_error = False

    def value(self) -> str:
        if self._positive.isChecked():
            return "+"
        if self._negative.isChecked():
            return "-"
        return ""

    def set_value(self, value: str) -> None:
        cleaned = (value or "").strip()
        if cleaned == "+":
            self._positive.setChecked(True)
        elif cleaned == "-":
            self._negative.setChecked(True)
        else:
            self._button_group.setExclusive(False)
            self._positive.setChecked(False)
            self._negative.setChecked(False)
            self._button_group.setExclusive(True)

    def set_error_state(self, has_error: bool) -> None:
        if self._has_error == has_error:
            return
        self._has_error = has_error
        for button in (self._positive, self._negative):
            button.setProperty("hasError", has_error)
            button.style().unpolish(button)
            button.style().polish(button)


class MenopauseStatusField(QWidget):
    """Widget that adapts available input based on patient sex."""

    _OPTIONS = [
        "postmenopausal",
        "premenopausal",
        "perimenopausal",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._stack = QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)

        readonly = QLineEdit(self)
        readonly.setReadOnly(True)
        readonly.setText("0")
        readonly.setAlignment(Qt.AlignCenter)
        readonly.setFocusPolicy(Qt.NoFocus)

        combo = QComboBox(self)
        combo.addItems(self._OPTIONS)

        self._stack.addWidget(readonly)
        self._stack.addWidget(combo)

        self.setLayout(self._stack)

        self._readonly_display = readonly
        self._options_combo = combo
        self._has_error = False

    def set_sex(self, sex: str) -> None:
        if sex == "Ж":
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)

    def value(self) -> str:
        if self._stack.currentIndex() == 0:
            return "0"
        return self._options_combo.currentText()

    def set_value(self, value: str) -> None:
        cleaned = (value or "").strip()
        if cleaned == "0":
            self._stack.setCurrentIndex(0)
            self._readonly_display.setText("0")
            return
        self._stack.setCurrentIndex(1)
        index = self._options_combo.findText(cleaned)
        if index >= 0:
            self._options_combo.setCurrentIndex(index)

    def set_error_state(self, has_error: bool) -> None:
        if self._has_error == has_error:
            return
        self._has_error = has_error
        for widget in (self._readonly_display, self._options_combo):
            widget.setProperty("hasError", has_error)
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class NClassificationField(QWidget):
    """Composite widget for selecting clinical or pathological N category."""

    _C_OPTIONS = [
        "cN — клиническая классификация (до операции)",
        "cNx — Состояние лимфоузлов не может быть оценено (например, удалены ранее).",
        "cN0 — Нет признаков поражения метастазами регионарных лимфоузлов по данным клинического обследования.",
        "cN1 — Метастазы в смещаемых подмышечных лимфоузлах I–II уровней.",
        "cN1mi — Микрометастазы (опухоль > 0,2 мм, но < 2 мм).",
        "cN2 — Метастазы в подмышечных лимфоузлах I–II уровней, спаянных между собой или фиксированных к тканям, или Метастазы во внутренних маммарных (парастернальных) лимфоузлах без поражения подмышечных.",
        "cN2a — Метастазы в подмышечных лимфоузлах I–II уровней, спаянные/фиксированные.",
        "cN2b — Метастазы во внутренних маммарных лимфоузлах при отсутствии поражения подмышечных.",
        "cN3 — Метастазы в: подключичных (III уровень), или внутренних маммарных + подмышечных лимфоузлах, или надключичных лимфоузлах (независимо от других).",
        "cN3a — Метастазы в подключичных лимфоузлах.",
        "cN3b — Метастазы во внутренних маммарных и подмышечных лимфоузлах.",
        "cN3c — Метастазы в надключичных лимфоузлах.",
    ]

    _P_OPTIONS = [
        "pN — патологическая классификация (после операции)",
        "pNx — Лимфоузлы не исследованы (не удалены или удалены ранее).",
        "pN0 — Нет метастазов в лимфоузлах.",
        "pN0(i+) — Только изолированные опухолевые клетки (≤ 0,2 мм).",
        "pN0(mol+) — Положительные молекулярные маркеры (ПЦР), но нет микроскопически видимых опухолевых клеток.",
        "pN1 — Метастазы в 1–3 подмышечных лимфоузлах или микро-/макрометастазы в внутренних маммарных узлах (при негативных подмышечных).",
        "pN1mi — Микрометастазы (> 0,2 мм, но < 2 мм).",
        "pN1a — Метастазы в 1–3 подмышечных лимфоузлах (хотя бы один > 2 мм).",
        "pN1b — Метастазы в внутренних маммарных сентинельных узлах (без изолированных клеток).",
        "pN1c — Признаки pN1a и pN1b одновременно.",
        "pN2 — Метастазы в 4–9 подмышечных лимфоузлах, или Поражение внутренних маммарных узлов при отсутствии поражения подмышечных.",
        "pN2a — Метастазы в 4–9 подмышечных лимфоузлах (≥ 2 мм).",
        "pN2b — Клинически выявленное поражение внутренних маммарных узлов (± микроскопическое подтверждение) без поражения подмышечных.",
        "pN3 — Метастазы в ≥10 подмышечных узлах, или В подключичных узлах, или В надключичных узлах, или Комбинация поражений (подмышечные + внутренние маммарные и др.).",
        "pN3a — Метастазы в ≥10 подмышечных или подключичных лимфоузлах.",
        "pN3b — pN1a/pN2a + cN2b или pN2a + pN1b.",
        "pN3c — Метастазы в надключичных лимфоузлах.",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        radio_layout = QHBoxLayout()
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(12)

        self._button_group = QButtonGroup(self)
        self._c_radio = QRadioButton("cN", self)
        self._p_radio = QRadioButton("pN", self)
        self._c_radio.setChecked(True)
        self._button_group.addButton(self._c_radio)
        self._button_group.addButton(self._p_radio)

        radio_layout.addWidget(self._c_radio)
        radio_layout.addWidget(self._p_radio)
        radio_layout.addStretch(1)

        self._stack = QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._c_combo = QComboBox(self)
        self._c_combo.addItems(self._C_OPTIONS)
        self._configure_combo(self._c_combo)

        self._p_combo = QComboBox(self)
        self._p_combo.addItems(self._P_OPTIONS)
        self._configure_combo(self._p_combo)

        self._stack.addWidget(self._c_combo)
        self._stack.addWidget(self._p_combo)

        self._c_radio.toggled.connect(self._on_type_changed)

        main_layout.addLayout(radio_layout)
        main_layout.addLayout(self._stack)
        self.setLayout(main_layout)
        self._has_error = False

    def _on_type_changed(self, checked: bool) -> None:
        if checked:
            self._stack.setCurrentIndex(0)
        else:
            self._stack.setCurrentIndex(1)

    def value(self) -> str:
        if self._stack.currentIndex() == 0:
            return self._c_combo.currentText()
        return self._p_combo.currentText()

    @staticmethod
    def _configure_combo(combo: QComboBox) -> None:
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.view().setTextElideMode(Qt.ElideNone)
        combo.setMinimumWidth(360)

    def set_value(self, value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            return
        combos = (self._c_combo, self._p_combo)
        for index, combo in enumerate(combos):
            match_index = combo.findText(cleaned)
            if match_index < 0:
                match_index = combo.findText(cleaned, Qt.MatchStartsWith)
            if match_index >= 0:
                if index == 0:
                    self._c_radio.setChecked(True)
                else:
                    self._p_radio.setChecked(True)
                combo.setCurrentIndex(match_index)
                self._stack.setCurrentIndex(index)
                return

    def set_error_state(self, has_error: bool) -> None:
        if self._has_error == has_error:
            return
        self._has_error = has_error
        for widget in (
            self._c_radio,
            self._p_radio,
            self._c_combo,
            self._p_combo,
        ):
            widget.setProperty("hasError", has_error)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
