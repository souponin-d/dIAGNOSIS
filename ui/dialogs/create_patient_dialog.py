"""Dialog for creating a new patient entry."""

from __future__ import annotations

from datetime import datetime, date
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)


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
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(12)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)

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

        data: Dict[str, str] = {}
        for label in self._field_order:
            value = self._read_value(self._inputs[label])
            if isinstance(value, dict):
                data.update(value)
            else:
                data[label] = value
        return data

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

    def value(self) -> str:
        if self._positive.isChecked():
            return "+"
        if self._negative.isChecked():
            return "-"
        return ""


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

    def set_sex(self, sex: str) -> None:
        if sex == "Ж":
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)

    def value(self) -> str:
        if self._stack.currentIndex() == 0:
            return "0"
        return self._options_combo.currentText()


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
