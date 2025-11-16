"""Main application window."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCharts import QCategoryAxis, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QEvent, QEasingCurve, QMargins, QPropertyAnimation, QPoint, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsColorizeEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget
)

try:
    from PySide6.QtWidgets import QWIDGETSIZE_MAX
except ImportError:  # pragma: no cover - fallback for PySide6 versions without the constant
    QWIDGETSIZE_MAX = (1 << 24) - 1

from config import AppConfig
from services.regression import regression_V_no_treatment
from ui.dialogs.create_patient_dialog import CreatePatientDialog


class HoverIconButton(QPushButton):
    """Push button that lightens its icon when hovered."""

    def __init__(
        self,
        *args,
        hover_strength: float = 0.35,
        animation_duration: int = 150,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._hover_strength = hover_strength
        self._hover_animation = QPropertyAnimation(self)
        self._hover_effect = QGraphicsColorizeEffect(self)
        self._hover_effect.setColor(Qt.white)
        self._hover_effect.setStrength(0.0)
        self.setGraphicsEffect(self._hover_effect)

        self._hover_animation.setTargetObject(self._hover_effect)
        self._hover_animation.setPropertyName(b"strength")
        self._hover_animation.setDuration(animation_duration)
        self._hover_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def enterEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        self._animate_hover(self._hover_strength)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def _animate_hover(self, value: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setEndValue(value)
        self._hover_animation.start()


class MainWindow(QMainWindow):
    """Primary window displaying the start screen with background and menu."""

    _BACKGROUND_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "background.png"
    _ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "logo.png"
    _MENU_EXPANDED_WIDTH = 240
    _CLOSE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "close_back.png"
    _CREATE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "create_back.png"
    _MORE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "more_back.png"
    _GROWTH_TABLE_HEADERS = ("Нач.", "3м", "6м", "12м", "24м")

    def __init__(self, config: AppConfig, application: Optional[QApplication] = None) -> None:
        super().__init__()
        self._config = config
        self._application = application

        self.setWindowTitle("dIAGNOSIS")
        self.setWindowIcon(QIcon(str(self._ICON_PATH)))
        self.resize(720, 480)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._background_label: QLabel | None = None
        self._background_pixmap: QPixmap | None = None
        self._menu_widget: QWidget | None = None
        self._content_widget: QWidget | None = None
        self._menu_animation: QPropertyAnimation | None = None
        self._menu_expanded = False
        self._menu_toggle_button: QToolButton | None = None
        self._tab_widget: QTabWidget | None = None
        self._section_pages: dict[str, QWidget] = {}
        self._section_buttons: dict[str, QPushButton] = {}
        self._header_label: QLabel | None = None
        self._current_section: str | None = None
        self._startup_view = True
        self._drag_position: QPoint | None = None
        self._startup_button_container: QWidget | None = None
        self._close_button: HoverIconButton | None = None
        self._overlay_widget: QWidget | None = None
        self._overlay_margins: QMargins | None = None
        self._patient_data: dict[str, str] = {}
        self._patient_placeholder_label: QLabel | None = None
        self._patient_details_widget: QWidget | None = None
        self._patient_details_form: QFormLayout | None = None
        self._stage_value_label: QLabel | None = None
        self._growth_table: QTableWidget | None = None
        self._growth_chart_view: QChartView | None = None
        self._growth_series: QLineSeries | None = None
        self._growth_axis_x: QCategoryAxis | None = None
        self._growth_axis_y: QValueAxis | None = None

        self._init_ui()
        self._center_on_screen()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setContentsMargins(0, 0, 0, 0)
        central_widget.setAttribute(Qt.WA_StyledBackground, True)
        central_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(central_widget)

        layout = QStackedLayout(central_widget)
        layout.setStackingMode(QStackedLayout.StackAll)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._background_label = QLabel(central_widget)
        self._background_label.setAlignment(Qt.AlignCenter)
        self._background_label.setContentsMargins(0, 0, 0, 0)
        self._background_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._background_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._background_label)

        overlay_widget = QWidget(central_widget)
        overlay_widget.setAttribute(Qt.WA_StyledBackground, True)
        overlay_widget.setStyleSheet("background-color: transparent;")
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(48, 48, 48, 48)
        overlay_layout.setSpacing(0)
        self._overlay_widget = overlay_widget
        self._overlay_margins = overlay_layout.contentsMargins()

        button_container = QWidget(overlay_widget)
        button_container.setAttribute(Qt.WA_StyledBackground, True)
        button_container.setStyleSheet(
            """
            background-color: transparent;
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 40);
                border-radius: 16px;
            }
            """
        )
        button_container.setFixedSize(780, 700)

        self._close_button = HoverIconButton(overlay_widget)
        self._close_button.setCursor(Qt.PointingHandCursor)
        self._close_button.setFlat(True)
        self._close_button.setToolTip("Закрыть")
        self._set_startup_button_icon(self._close_button, self._CLOSE_ICON_PATH)
        self._close_button.clicked.connect(self.close)
        self._close_button.raise_()
        self._position_close_button()

        create_button = HoverIconButton(button_container)
        create_button.setCursor(Qt.PointingHandCursor)
        create_button.setFlat(True)
        create_button.setToolTip("Создать проект")
        self._set_startup_button_icon(create_button, self._CREATE_ICON_PATH)
        create_button.clicked.connect(self._open_create_dialog)
        create_button.move(103, 207)

        more_button = HoverIconButton(button_container)
        more_button.setCursor(Qt.PointingHandCursor)
        more_button.setFlat(True)
        more_button.setToolTip("Дополнительно")
        self._set_startup_button_icon(more_button, self._MORE_ICON_PATH)
        more_button.move(178, 207)

        overlay_layout.addStretch()
        overlay_layout.addWidget(button_container, alignment=Qt.AlignHCenter)
        overlay_layout.addStretch()

        layout.addWidget(overlay_widget)
        overlay_widget.raise_()
        self._startup_button_container = button_container

        pixmap = QPixmap(str(self._BACKGROUND_PATH))
        if not pixmap.isNull():
            self._background_pixmap = pixmap
            self._apply_startup_background_size()
            self._update_background_pixmap()

        self.menuBar().hide()

    def _set_startup_button_icon(self, button: QPushButton, icon_path: Path) -> None:
        pixmap = QPixmap(str(icon_path))
        if pixmap.isNull():
            return

        original_size = pixmap.size()
        if not original_size.isValid():
            return

        scaled_width = max(int(original_size.width() / 2.5), 1)
        scaled_height = max(int(original_size.height() / 2.5), 1)
        scaled_pixmap = pixmap.scaled(
            QSize(scaled_width, scaled_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        icon = QIcon(scaled_pixmap)
        button.setIcon(icon)
        button.setIconSize(scaled_pixmap.size())
        button.setFixedSize(scaled_pixmap.size())

    def _position_close_button(self) -> None:
        if not self._close_button:
            return

        parent = self._close_button.parentWidget()
        if not parent:
            return

        margins = self._overlay_margins or QMargins(0, 0, 0, 0)
        y_offset = max(margins.top() - 40, 0)
        x_offset = max(parent.width() - self._close_button.width() - margins.right(), 0)
        self._close_button.move(x_offset, y_offset)

    def _center_on_screen(self) -> None:
        app = self._application or QApplication.instance()
        if not app:
            return

        screen = app.primaryScreen()
        if not screen:
            return

        geometry = self.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.clear()
        menu_bar.show()

        file_menu = menu_bar.addMenu("Файл")

        create_action = QAction("Создать...", self)
        create_action.triggered.connect(self._open_create_dialog)
        file_menu.addAction(create_action)

        open_action = QAction("Открыть...", self)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить", self)
        save_action.setEnabled(False)
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить как...", self)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        close_project_action = QAction("Закрыть проект", self)
        close_project_action.setEnabled(False)
        file_menu.addAction(close_project_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("Помощь")

        version_action = QAction("Версия...", self)
        version_action.setEnabled(False)
        help_menu.addAction(version_action)

        help_action = QAction("Справка", self)
        help_action.setEnabled(False)
        help_menu.addAction(help_action)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._update_background_pixmap()
        self._position_close_button()

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_background_pixmap()
        self._position_close_button()

    def _open_create_dialog(self) -> None:
        dialog = CreatePatientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._patient_data = dialog.collected_data()
            self._transition_to_full_screen()
            self._refresh_patient_information_view()

    def _apply_startup_background_size(self) -> None:
        if not self._startup_view:
            return

        if not self._background_pixmap or self._background_pixmap.isNull():
            return

        pixmap_size = self._background_pixmap.size()
        if not pixmap_size.isValid():
            return

        desired_width = max(int(pixmap_size.width() / 2.5), 1)
        desired_height = max(int(pixmap_size.height() / 2.5), 1)
        desired_size = QSize(desired_width, desired_height)

        app = self._application or QApplication.instance()
        screen_size = QSize()
        if app:
            screen = app.primaryScreen()
            if screen:
                screen_size = screen.availableGeometry().size()

        if screen_size.isValid() and (
            desired_size.width() > screen_size.width()
            or desired_size.height() > screen_size.height()
        ):
            desired_size = desired_size.scaled(screen_size, Qt.KeepAspectRatio)

        self.resize(desired_size)
        self.setFixedSize(desired_size)

    def _update_background_pixmap(self) -> None:
        if not self._background_label:
            return

        if not self._background_pixmap or self._background_pixmap.isNull():
            return

        central_widget = self.centralWidget()
        if central_widget is None:
            return

        available_size = central_widget.size()
        if not available_size.isValid():
            return

        self._background_label.resize(available_size)
        self._background_label.move(0, 0)

        original_size = self._background_pixmap.size()
        if not original_size.isValid():
            return

        reduced_width = max(int(original_size.width() / 2.5), 1)
        reduced_height = max(int(original_size.height() / 2.5), 1)
        desired_size = QSize(reduced_width, reduced_height)

        if desired_size.width() > available_size.width() or desired_size.height() > available_size.height():
            desired_size = desired_size.scaled(available_size, Qt.KeepAspectRatio)

        scaled_pixmap = self._background_pixmap.scaled(
            desired_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self._background_label.setPixmap(scaled_pixmap)

    def _transition_to_full_screen(self) -> None:
        if not self._startup_view:
            return

        if self._background_label:
            self._background_label.hide()
            self._background_label.deleteLater()
            self._background_label = None
            self._background_pixmap = None

        if self._startup_button_container:
            self._startup_button_container.hide()
            self._startup_button_container.deleteLater()
            self._startup_button_container = None

        self._startup_view = False
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowFlag(Qt.FramelessWindowHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.show()

        previous_central_widget = self.centralWidget()
        project_widget = QWidget(self)
        project_widget.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(project_widget)

        if previous_central_widget is not None:
            previous_central_widget.deleteLater()

        self._init_project_view(project_widget)
        self._create_menus()
        self.showMaximized()

    def _init_project_view(self, project_widget: QWidget) -> None:
        project_widget.setAttribute(Qt.WA_StyledBackground, True)
        project_widget.setStyleSheet("background-color: #d9d9d9;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        project_widget.setLayout(layout)

        self._menu_widget = QWidget(project_widget)
        self._menu_widget.setMinimumWidth(0)
        self._menu_widget.setMaximumWidth(0)
        self._menu_widget.setStyleSheet("background-color: #1a1a1a;")

        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(16, 32, 16, 16)
        menu_layout.setSpacing(12)
        self._menu_widget.setLayout(menu_layout)

        sections = ("Информация", "Терапия", "Прогноз")
        self._section_pages = {}
        self._section_buttons = {}

        for section in sections:
            section_button = QPushButton(section, self._menu_widget)
            section_button.setCursor(Qt.PointingHandCursor)
            section_button.setStyleSheet(self._menu_button_style(False))
            section_button.setFlat(True)
            section_button.clicked.connect(
                lambda _checked=False, name=section: self._activate_section(name)
            )
            menu_layout.addWidget(section_button)
            self._section_buttons[section] = section_button

        menu_layout.addStretch()

        layout.addWidget(self._menu_widget)

        self._content_widget = QWidget(project_widget)
        self._content_widget.setAttribute(Qt.WA_StyledBackground, True)
        self._content_widget.setStyleSheet("background-color: #d9d9d9;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        self._content_widget.setLayout(content_layout)

        layout.addWidget(self._content_widget, 1)

        top_bar = QWidget(self._content_widget)
        top_bar.setAttribute(Qt.WA_StyledBackground, True)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        top_bar.setLayout(top_layout)

        self._menu_toggle_button = QToolButton(top_bar)
        self._menu_toggle_button.setText("☰")
        self._menu_toggle_button.setToolTip("Меню")
        self._menu_toggle_button.setCheckable(True)
        self._menu_toggle_button.setFixedSize(40, 40)
        self._menu_toggle_button.clicked.connect(self._toggle_menu)
        top_layout.addWidget(self._menu_toggle_button)

        self._header_label = QLabel("", top_bar)
        self._header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._header_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #2b2b2b;")
        top_layout.addWidget(self._header_label)
        top_layout.addStretch()

        content_layout.addWidget(top_bar)

        self._tab_widget = QTabWidget(self._content_widget)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setStyleSheet(
            "QTabWidget::pane { background: #d9d9d9; border: none; }"
        )
        if tab_bar := self._tab_widget.tabBar():
            tab_bar.hide()
        self._tab_widget.currentChanged.connect(self._handle_tab_changed)
        content_layout.addWidget(self._tab_widget, 1)

        info_tab, info_layout = self._create_tab()

        info_columns = QHBoxLayout()
        info_columns.setContentsMargins(0, 0, 0, 0)
        info_columns.setSpacing(24)
        info_layout.addLayout(info_columns, 1)

        left_column = QWidget(info_tab)
        left_column_layout = QVBoxLayout()
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        left_column_layout.setSpacing(16)
        left_column.setLayout(left_column_layout)

        patient_title = QLabel("Данные пациента", left_column)
        patient_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        left_column_layout.addWidget(patient_title)

        self._patient_placeholder_label = QLabel(
            "Информация появится после заполнения формы.",
            left_column,
        )
        self._patient_placeholder_label.setWordWrap(True)
        left_column_layout.addWidget(self._patient_placeholder_label)

        self._patient_details_form = QFormLayout()
        self._patient_details_form.setContentsMargins(0, 0, 0, 0)
        self._patient_details_form.setSpacing(6)
        self._patient_details_form.setLabelAlignment(Qt.AlignLeft)
        self._patient_details_widget = QWidget(left_column)
        self._patient_details_widget.setLayout(self._patient_details_form)
        self._patient_details_widget.hide()
        left_column_layout.addWidget(self._patient_details_widget)

        stage_container = QWidget(left_column)
        stage_layout = QHBoxLayout()
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(12)
        stage_container.setLayout(stage_layout)

        stage_label = QLabel("Стадия:", stage_container)
        stage_label.setStyleSheet("font-size: 16px;")
        stage_layout.addWidget(stage_label)

        self._stage_value_label = QLabel("—", stage_container)
        self._stage_value_label.setStyleSheet("font-size: 24px; font-weight: 600;")
        stage_layout.addWidget(self._stage_value_label)
        stage_layout.addStretch(1)

        left_column_layout.addWidget(stage_container)

        table_title = QLabel("Динамика наблюдения", left_column)
        table_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        left_column_layout.addWidget(table_title)

        self._growth_table = self._create_growth_table(left_column)
        left_column_layout.addWidget(self._growth_table)
        left_column_layout.addStretch(1)

        left_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        info_columns.addWidget(left_column)

        right_column = QWidget(info_tab)
        right_column_layout = QVBoxLayout()
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        right_column_layout.setSpacing(12)
        right_column.setLayout(right_column_layout)

        right_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._growth_chart_view = self._create_growth_chart(right_column)
        right_column_layout.addWidget(self._growth_chart_view, 1)

        info_columns.addWidget(right_column)
        info_columns.setStretch(0, 1)
        info_columns.setStretch(1, 1)

        self._refresh_patient_information_view()

        self._recalculate_growth_data()

        self._tab_widget.addTab(info_tab, "Информация")
        self._section_pages["Информация"] = info_tab

        for section in sections[1:]:
            section_tab, section_layout = self._create_tab()
            section_label = QLabel("Раздел в разработке", section_tab)
            section_label.setAlignment(Qt.AlignCenter)
            section_label.setStyleSheet("font-size: 18px; color: #444;")
            section_layout.addStretch()
            section_layout.addWidget(section_label, alignment=Qt.AlignCenter)
            section_layout.addStretch()
            self._tab_widget.addTab(section_tab, section)
            self._section_pages[section] = section_tab

        self._menu_animation = QPropertyAnimation(self._menu_widget, b"maximumWidth", self)
        self._menu_animation.setDuration(250)
        self._menu_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._menu_expanded = False

        if sections:
            self._update_active_section(sections[0])

    def _create_tab(self) -> tuple[QWidget, QVBoxLayout]:
        tab = QWidget(self._tab_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        tab.setLayout(layout)
        return tab, layout

    def _menu_button_style(self, active: bool) -> str:
        if active:
            return (
                """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #1a1a1a;
                    border: none;
                    text-align: left;
                    padding: 10px 14px;
                    border-radius: 6px;
                    font-weight: 600;
                }
                """
            )
        return (
            """
            QPushButton {
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: none;
                text-align: left;
                padding: 10px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            """
        )

    def _toggle_menu(self, checked: bool = False) -> None:  # noqa: ARG002 - checked managed manually
        if not self._menu_widget or not self._menu_animation:
            return

        self._menu_animation.stop()

        start_width = self._menu_widget.width()
        if self._menu_expanded:
            end_width = 0
        else:
            end_width = self._MENU_EXPANDED_WIDTH
            self._menu_widget.setMaximumWidth(self._MENU_EXPANDED_WIDTH)

        self._menu_animation.setStartValue(start_width)
        self._menu_animation.setEndValue(end_width)
        self._menu_animation.start()

        self._menu_expanded = not self._menu_expanded
        if self._menu_toggle_button:
            self._menu_toggle_button.setChecked(self._menu_expanded)

    def _handle_tab_changed(self, index: int) -> None:
        if not self._tab_widget:
            return

        section = self._tab_widget.tabText(index)
        if section:
            self._update_active_section(section)

    def _update_active_section(self, section: str) -> None:
        self._current_section = section

        if self._header_label:
            self._header_label.setText(section)

        for name, button in self._section_buttons.items():
            button.setStyleSheet(self._menu_button_style(name == section))

    def _activate_section(self, section: str) -> None:
        if not self._tab_widget:
            return

        page = self._section_pages.get(section)
        if not page:
            return

        index = self._tab_widget.indexOf(page)
        if index != -1:
            self._tab_widget.setCurrentIndex(index)
            self._update_active_section(section)

    def _create_growth_table(self, parent: QWidget) -> QTableWidget:
        table = QTableWidget(1, len(self._GROWTH_TABLE_HEADERS), parent)
        table.setHorizontalHeaderLabels(self._GROWTH_TABLE_HEADERS)
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setFrameShape(QFrame.NoFrame)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        for column in range(table.columnCount()):
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, column, item)

        return table

    def _create_growth_chart(self, parent: QWidget) -> QChartView:
        self._growth_series = QLineSeries()
        chart = QChart()
        chart.addSeries(self._growth_series)
        chart.legend().hide()
        chart.setTitle("Оценка изменения объёма опухоли без лечения")
        chart.setBackgroundVisible(True)
        chart.setBackgroundBrush(Qt.white)
        chart.setPlotAreaBackgroundBrush(Qt.white)
        chart.setPlotAreaBackgroundVisible(True)

        self._growth_axis_x = QCategoryAxis()
        self._growth_axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        for index, header in enumerate(self._GROWTH_TABLE_HEADERS):
            self._growth_axis_x.append(header, float(index))
        if self._GROWTH_TABLE_HEADERS:
            self._growth_axis_x.setRange(0.0, float(len(self._GROWTH_TABLE_HEADERS) - 1))
        chart.addAxis(self._growth_axis_x, Qt.AlignBottom)
        self._growth_series.attachAxis(self._growth_axis_x)

        self._growth_axis_y = QValueAxis()
        self._growth_axis_y.setLabelFormat("%.1f")
        chart.addAxis(self._growth_axis_y, Qt.AlignLeft)
        self._growth_series.attachAxis(self._growth_axis_y)

        chart_view = QChartView(chart, parent)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_view.setStyleSheet("background-color: white; border: none;")

        return chart_view

    def _update_growth_chart_from_table(self) -> None:
        if not self._growth_table or not self._growth_series:
            return

        self._growth_series.clear()
        values: list[float] = []
        for column in range(self._growth_table.columnCount()):
            item = self._growth_table.item(0, column)
            if not item:
                continue
            try:
                value = float(item.text().replace(",", "."))
            except ValueError:
                continue
            values.append(value)
            self._growth_series.append(float(column), value)

        if not self._growth_axis_y:
            return

        if values:
            minimum = min(values)
            maximum = max(values)
            margin = max((maximum - minimum) * 0.1, 1.0)
            self._growth_axis_y.setRange(minimum - margin, maximum + margin)
        else:
            self._growth_axis_y.setRange(0.0, 1.0)

    def _recalculate_growth_data(self) -> None:
        if not self._growth_table:
            return

        if not self._patient_data:
            self._set_growth_table_values([])
            self._update_growth_chart_from_table()
            return

        values = regression_V_no_treatment(self._patient_data)
        self._set_growth_table_values(values)
        self._update_growth_chart_from_table()

    def _set_growth_table_values(self, values: Sequence[float]) -> None:
        if not self._growth_table:
            return

        column_count = self._growth_table.columnCount()
        for column in range(column_count):
            if column < len(values):
                numeric_value = values[column]
                text = f"{numeric_value:.2f}".rstrip("0").rstrip(".")
            else:
                text = "—"

            item = self._growth_table.item(0, column)
            if not item:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                self._growth_table.setItem(0, column, item)
            item.setText(text)

    def _refresh_patient_information_view(self) -> None:
        if (
            not self._patient_details_form
            or not self._patient_details_widget
            or not self._patient_placeholder_label
        ):
            return

        while self._patient_details_form.rowCount():
            self._patient_details_form.removeRow(0)

        if self._stage_value_label:
            self._stage_value_label.setText("—")

        if not self._patient_data:
            self._patient_details_widget.hide()
            self._patient_placeholder_label.show()
            self._recalculate_growth_data()
            return

        for label, value in self._patient_data.items():
            name_label = QLabel(label, self._patient_details_widget)
            name_label.setWordWrap(True)
            value_label = QLabel(value or "—", self._patient_details_widget)
            value_label.setStyleSheet("font-weight: 600;")
            value_label.setWordWrap(True)
            value_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            self._patient_details_form.addRow(name_label, value_label)

        stage_value = self._calculate_stage()
        if self._stage_value_label:
            self._stage_value_label.setText(stage_value)

        self._patient_placeholder_label.hide()
        self._patient_details_widget.show()
        self._recalculate_growth_data()

    def _calculate_stage(self) -> str:
        if not self._patient_data:
            return "—"

        t_category = self._normalize_category(self._patient_data.get("T", ""), "T")
        n_category = self._normalize_category(self._patient_data.get("N", ""), "N")
        m_category = self._normalize_category(self._patient_data.get("M", ""), "M")

        if not (t_category and n_category and m_category):
            return "—"

        if m_category == "M1":
            return "IV"
        if n_category == "N3" and m_category == "M0":
            return "IIIC"

        rules = [
            ("Tis", "N0", "M0", "0"),
            ("T1", "N0", "M0", "IA"),
            ("T0", "N1mi", "M0", "IB"),
            ("T1", "N1mi", "M0", "IB"),
            ("T0", "N1", "M0", "IIA"),
            ("T1", "N1", "M0", "IIA"),
            ("T2", "N0", "M0", "IIA"),
            ("T2", "N1", "M0", "IIB"),
            ("T3", "N0", "M0", "IIB"),
            ("T0", "N2", "M0", "IIIA"),
            ("T1", "N2", "M0", "IIIA"),
            ("T2", "N2", "M0", "IIIA"),
            ("T3", "N1", "M0", "IIIA"),
            ("T3", "N2", "M0", "IIIA"),
            ("T4", "N0", "M0", "IIIB"),
            ("T4", "N1", "M0", "IIIB"),
            ("T4", "N2", "M0", "IIIB"),
        ]

        for t_rule, n_rule, m_rule, stage in rules:
            if t_category == t_rule and n_category == n_rule and m_category == m_rule:
                return stage

        return "—"

    @staticmethod
    def _normalize_category(value: str, category_type: str) -> str:
        if not value:
            return ""

        head = value.split("—", 1)[0].strip()
        head = head.split(" ", 1)[0].strip()

        if not head:
            return ""

        if category_type == "T":
            if head.lower().startswith("tis"):
                return "Tis"
            match = re.match(r"(T\\d+)", head)
            if match:
                return match.group(1)
            return head if head.startswith("T") else ""

        if category_type == "N":
            if head.startswith(("c", "p")) and len(head) > 1:
                head = head[1:]
            mi_match = re.match(r"(N\\d+mi)", head)
            if mi_match:
                return mi_match.group(1)
            match = re.match(r"(N\\d+)", head)
            if match:
                return match.group(1)
            return head if head.startswith("N") else ""

        if category_type == "M":
            if head.startswith(("c", "p")) and len(head) > 1:
                head = head[1:]
            match = re.match(r"(M\\d)", head)
            if match:
                return match.group(1)
            return head if head.startswith("M") else ""

        return ""

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._startup_view and event.button() == Qt.LeftButton:
            widget = self.childAt(event.position().toPoint())
            while widget is not None:
                if isinstance(widget, (QPushButton, QToolButton)):
                    break
                widget = widget.parentWidget()
            else:
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if (
            self._startup_view
            and self._drag_position is not None
            and event.buttons() & Qt.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._startup_view and event.button() == Qt.LeftButton:
            self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._startup_view and event.button() == Qt.LeftButton:
            self._open_create_dialog()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if self._startup_view and event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)
