"""Main application window."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCharts import (
    QAreaSeries,
    QCategoryAxis,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import (
    QEvent,
    QEasingCurve,
    QMargins,
    QPropertyAnimation,
    QPoint,
    QPointF,
    QSize,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QColor,
    QPen,
)
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
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget
)

try:
    from PySide6.QtWidgets import QWIDGETSIZE_MAX
except ImportError:  # pragma: no cover - fallback for PySide6 versions without the constant
    QWIDGETSIZE_MAX = (1 << 24) - 1

from config import AppConfig
from core.patient_features import calculate_age, calculate_stage, normalize_category
from services.regression import (
    regression_V_no_treatment,
    regression_V_no_treatment_with_ci,
)
from services.therapy import (
    format_therapy_recommendations,
    generate_treatment_recommendations,
)
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


class HoverIconToolButton(QToolButton):
    """Tool button that mimics the hover glow of the startup buttons."""

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
    _MENU_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "menu.png"
    _CLOSE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "close_back.png"
    _CREATE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "create_back.png"
    _MORE_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "more_back.png"
    _GROWTH_TABLE_HEADERS = ("Нач.", "3м", "6м", "12м", "24м")
    _GROWTH_ANIMATION_DURATION_MS = 1600

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
        self._menu_toggle_button: HoverIconToolButton | None = None
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
        self._edit_patient_button: QPushButton | None = None
        self._stage_value_label: QLabel | None = None
        self._molecular_subtype_value_label: QLabel | None = None
        self._growth_table: QTableWidget | None = None
        self._growth_chart_view: QChartView | None = None
        self._growth_series: QLineSeries | None = None
        self._growth_ci_upper_series: QLineSeries | None = None
        self._growth_ci_lower_series: QLineSeries | None = None
        self._growth_ci_area: QAreaSeries | None = None
        self._growth_axis_x: QCategoryAxis | None = None
        self._growth_axis_y: QValueAxis | None = None
        self._growth_animation: QVariantAnimation | None = None
        self._growth_animation_points: list[tuple[float, float]] = []
        self._growth_ci_animation_points_low: list[tuple[float, float]] = []
        self._growth_ci_animation_points_high: list[tuple[float, float]] = []
        self._therapy_log_view: QTextBrowser | None = None

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

    def _configure_menu_toggle_button(self) -> None:
        if not self._menu_toggle_button:
            return

        self._menu_toggle_button.setCursor(Qt.PointingHandCursor)
        self._menu_toggle_button.setStyleSheet(
            """
            QToolButton {
                border: none;
                background-color: transparent;
                padding: 0;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 25);
                border-radius: 12px;
            }
            QToolButton:checked {
                background-color: rgba(0, 0, 0, 40);
                border-radius: 12px;
            }
            """
        )

        pixmap = QPixmap(str(self._MENU_ICON_PATH))
        if pixmap.isNull():
            self._menu_toggle_button.setText("☰")
            self._menu_toggle_button.setFixedSize(self._menu_toggle_button.sizeHint())
            return

        icon_size = QSize(48, 48)
        scaled_pixmap = pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._menu_toggle_button.setIcon(QIcon(scaled_pixmap))
        self._menu_toggle_button.setIconSize(icon_size)
        self._menu_toggle_button.setText("")
        self._menu_toggle_button.setFixedSize(icon_size)

    def _position_close_button(self) -> None:
        if not self._close_button:
            return

        parent = self._close_button.parentWidget()
        if not parent:
            return

        margins = self._overlay_margins or QMargins(0, 0, 0, 0)
        y_offset = max(margins.top() - 28, 0)
        x_offset = max(parent.width() - self._close_button.width() - margins.right() + 27, 0)
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
        create_action.setEnabled(False)
        file_menu.addAction(create_action)

        open_action = QAction("Открыть...", self)
        open_action.setEnabled(False)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить", self)
        save_action.setEnabled(False)
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить как...", self)
        save_as_action.setEnabled(False)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        close_project_action = QAction("Закрыть проект", self)
        close_project_action.setEnabled(False)
        file_menu.addAction(close_project_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        exit_action.setEnabled(False)
        file_menu.addAction(exit_action)

        file_menu.menuAction().setEnabled(False)

        help_menu = menu_bar.addMenu("Помощь")

        version_action = QAction("Версия...", self)
        version_action.setEnabled(False)
        help_menu.addAction(version_action)

        help_action = QAction("Справка", self)
        help_action.setEnabled(False)
        help_menu.addAction(help_action)

        help_menu.menuAction().setEnabled(False)

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

    def _open_edit_dialog(self) -> None:
        if not self._patient_data:
            self._open_create_dialog()
            return

        dialog = CreatePatientDialog(self, patient_data=self._patient_data, is_edit=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._patient_data = dialog.collected_data()
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

        if self._close_button:
            self._close_button.hide()
            self._close_button.deleteLater()
            self._close_button = None

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
        self._content_widget.setStyleSheet("background-color: #f2f2f2;")
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

        self._menu_toggle_button = HoverIconToolButton(top_bar)
        self._menu_toggle_button.setToolTip("Меню")
        self._menu_toggle_button.setCheckable(True)
        self._configure_menu_toggle_button()
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
            "QTabWidget::pane { background: transparent; border: none; }"
        )
        if tab_bar := self._tab_widget.tabBar():
            tab_bar.hide()
        self._tab_widget.currentChanged.connect(self._handle_tab_changed)
        content_layout.addWidget(self._tab_widget, 1)

        info_tab, info_layout = self._create_tab()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)

        info_background = QFrame(info_tab)
        info_background.setObjectName("infoBackground")
        info_background.setStyleSheet(
            "#infoBackground { background-color: #ffffff; border-radius: 24px; }"
        )
        info_background_layout = QVBoxLayout()
        info_background_layout.setContentsMargins(32, 32, 32, 32)
        info_background_layout.setSpacing(24)
        info_background.setLayout(info_background_layout)
        info_layout.addWidget(info_background)

        info_columns = QHBoxLayout()
        info_columns.setContentsMargins(0, 0, 0, 0)
        info_columns.setSpacing(32)
        info_background_layout.addLayout(info_columns, 1)

        patient_scroll = QScrollArea(info_tab)
        patient_scroll.setObjectName("patientInfoScroll")
        patient_scroll.setWidgetResizable(True)
        patient_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        patient_scroll.setStyleSheet(
            """
            #patientInfoScroll {
                border: none;
                background: transparent;
            }
            #patientInfoScroll QWidget {
                background: transparent;
            }
            #patientInfoScroll QScrollBar:vertical {
                width: 10px;
                background: transparent;
                margin: 12px 2px 12px 0;
            }
            #patientInfoScroll QScrollBar::handle:vertical {
                background: rgba(22, 52, 85, 140);
                border-radius: 5px;
                min-height: 30px;
            }
            #patientInfoScroll QScrollBar::handle:vertical:hover {
                background: rgba(22, 52, 85, 180);
            }
            #patientInfoScroll QScrollBar::add-line:vertical,
            #patientInfoScroll QScrollBar::sub-line:vertical,
            #patientInfoScroll QScrollBar::add-page:vertical,
            #patientInfoScroll QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
            """
        )

        patient_panel = QWidget(patient_scroll)
        patient_panel.setObjectName("patientInfoPanel")
        patient_panel.setStyleSheet(
            "#patientInfoPanel { background-color: #E0E9F2; border-radius: 24px; }"
        )
        patient_panel_layout = QVBoxLayout()
        patient_panel_layout.setContentsMargins(24, 24, 24, 24)
        patient_panel_layout.setSpacing(16)
        patient_panel.setLayout(patient_panel_layout)
        patient_scroll.setWidget(patient_panel)

        patient_header = QWidget(patient_panel)
        patient_header_layout = QHBoxLayout()
        patient_header_layout.setContentsMargins(0, 0, 0, 0)
        patient_header_layout.setSpacing(12)
        patient_header.setLayout(patient_header_layout)

        patient_title = QLabel("Информация о пациенте", patient_header)
        patient_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        patient_header_layout.addWidget(patient_title)
        patient_header_layout.addStretch(1)

        self._edit_patient_button = QPushButton("Редактировать", patient_header)
        self._edit_patient_button.setCursor(Qt.PointingHandCursor)
        self._edit_patient_button.setEnabled(False)
        self._edit_patient_button.setObjectName("editPatientButton")
        self._edit_patient_button.setStyleSheet(
            """
            QPushButton#editPatientButton {
                background-color: #ffffff;
                border: 1px solid #cbd3df;
                border-radius: 10px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton#editPatientButton:disabled {
                color: #9aa5b5;
                border-color: #e1e7ef;
            }
            """
        )
        self._edit_patient_button.clicked.connect(self._open_edit_dialog)
        patient_header_layout.addWidget(self._edit_patient_button)

        patient_panel_layout.addWidget(patient_header)

        self._patient_placeholder_label = QLabel(
            "Информация появится после заполнения формы.",
            patient_panel,
        )
        self._patient_placeholder_label.setWordWrap(True)
        patient_panel_layout.addWidget(self._patient_placeholder_label)

        self._patient_details_form = QFormLayout()
        self._patient_details_form.setContentsMargins(0, 0, 0, 0)
        self._patient_details_form.setSpacing(10)
        self._patient_details_form.setLabelAlignment(Qt.AlignLeft)
        self._patient_details_form.setFormAlignment(Qt.AlignTop)
        self._patient_details_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._patient_details_widget = QWidget(patient_panel)
        self._patient_details_widget.setLayout(self._patient_details_form)
        self._patient_details_widget.hide()
        patient_panel_layout.addWidget(self._patient_details_widget)
        patient_panel_layout.addStretch(1)

        patient_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        patient_column = QWidget(info_tab)
        patient_column_layout = QVBoxLayout()
        patient_column_layout.setContentsMargins(0, 0, 0, 0)
        patient_column_layout.setSpacing(12)
        patient_column.setLayout(patient_column_layout)

        analytics_column = QWidget(info_tab)
        analytics_column_layout = QVBoxLayout()
        analytics_column_layout.setContentsMargins(0, 0, 0, 0)
        analytics_column_layout.setSpacing(12)
        analytics_column.setLayout(analytics_column_layout)

        self._growth_chart_view = self._create_growth_chart(analytics_column)
        analytics_column_layout.addWidget(self._growth_chart_view, 1)

        analytics_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        patient_column.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        info_columns.addWidget(patient_column, 1)
        info_columns.addWidget(analytics_column, 2)

        patient_highlights = QFrame(info_tab)
        patient_highlights.setObjectName("patientHighlights")
        patient_highlights.setStyleSheet(
            "#patientHighlights { background-color: #ffffff; border-radius: 24px; }"
        )
        patient_highlights_layout = QVBoxLayout()
        patient_highlights_layout.setContentsMargins(24, 24, 24, 24)
        patient_highlights_layout.setSpacing(16)
        patient_highlights.setLayout(patient_highlights_layout)

        patient_column_layout.addWidget(patient_scroll)

        stage_container = QWidget(patient_highlights)
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

        patient_highlights_layout.addWidget(stage_container)

        subtype_container = QWidget(patient_highlights)
        subtype_layout = QHBoxLayout()
        subtype_layout.setContentsMargins(0, 0, 0, 0)
        subtype_layout.setSpacing(12)
        subtype_container.setLayout(subtype_layout)

        subtype_label = QLabel("Молекулярно-биологический подтип:", subtype_container)
        subtype_label.setStyleSheet("font-size: 16px;")
        subtype_layout.addWidget(subtype_label)

        self._molecular_subtype_value_label = QLabel("—", subtype_container)
        self._molecular_subtype_value_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )
        subtype_layout.addWidget(self._molecular_subtype_value_label)
        subtype_layout.addStretch(1)

        patient_highlights_layout.addWidget(subtype_container)

        table_title = QLabel("Динамика наблюдения", patient_highlights)
        table_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        patient_highlights_layout.addWidget(table_title)

        self._growth_table = self._create_growth_table(patient_highlights)
        patient_highlights_layout.addWidget(self._growth_table)
        patient_highlights_layout.addStretch(1)

        patient_column_layout.addWidget(patient_highlights)
        patient_column_layout.addStretch(1)

        self._refresh_patient_information_view()

        self._recalculate_growth_data()

        self._tab_widget.addTab(info_tab, "Информация")
        self._section_pages["Информация"] = info_tab

        for section in sections[1:]:
            section_tab, section_layout = self._create_tab()
            if section == "Терапия":
                therapy_background = QFrame(section_tab)
                therapy_background.setObjectName("therapyBackground")
                therapy_background.setStyleSheet(
                    "#therapyBackground { background-color: #ffffff; border-radius: 24px; }"
                )
                therapy_layout = QVBoxLayout()
                therapy_layout.setContentsMargins(32, 32, 32, 32)
                therapy_layout.setSpacing(16)
                therapy_background.setLayout(therapy_layout)

                therapy_title = QLabel("Рекомендации по терапии", therapy_background)
                therapy_title.setStyleSheet("font-size: 20px; font-weight: 600;")
                therapy_layout.addWidget(therapy_title)

                self._therapy_log_view = QTextBrowser(therapy_background)
                self._therapy_log_view.setObjectName("therapyOutput")
                self._therapy_log_view.setReadOnly(True)
                self._therapy_log_view.setStyleSheet(
                    """
                    QTextBrowser#therapyOutput {
                        background-color: #f5f7fb;
                        border: 1px solid #d6dce7;
                        border-radius: 12px;
                        font-size: 14px;
                        padding: 16px;
                    }
                    QTextBrowser#therapyOutput QScrollBar:vertical {
                        width: 10px;
                        background: transparent;
                        margin: 12px 2px 12px 0;
                    }
                    QTextBrowser#therapyOutput QScrollBar::handle:vertical {
                        background: rgba(22, 52, 85, 140);
                        border-radius: 5px;
                        min-height: 30px;
                    }
                    QTextBrowser#therapyOutput QScrollBar::handle:vertical:hover {
                        background: rgba(22, 52, 85, 180);
                    }
                    QTextBrowser#therapyOutput QScrollBar::add-line:vertical,
                    QTextBrowser#therapyOutput QScrollBar::sub-line:vertical,
                    QTextBrowser#therapyOutput QScrollBar::add-page:vertical,
                    QTextBrowser#therapyOutput QScrollBar::sub-page:vertical {
                        background: none;
                        border: none;
                    }
                    """
                )
                self._therapy_log_view.setHtml(
                    "<p style='color:#666;'>Рекомендации будут показаны после заполнения данных о пациенте.</p>"
                )
                therapy_layout.addWidget(self._therapy_log_view, 1)

                section_layout.addWidget(therapy_background)
            else:
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
        self._growth_ci_upper_series = QLineSeries()
        self._growth_ci_lower_series = QLineSeries()
        self._growth_ci_area = QAreaSeries(
            self._growth_ci_upper_series, self._growth_ci_lower_series
        )
        self._growth_ci_area.setName("95% ДИ")
        ci_color = QColor(52, 120, 206)
        ci_brush = QColor(ci_color)
        ci_brush.setAlphaF(0.18)
        self._growth_ci_area.setBrush(ci_brush)
        ci_pen = QPen(ci_color)
        ci_pen.setWidthF(1.0)
        ci_pen.setStyle(Qt.DashLine)
        self._growth_ci_area.setPen(ci_pen)
        self._growth_ci_area.setVisible(False)

        chart = QChart()
        chart.addSeries(self._growth_ci_area)
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
        self._growth_ci_area.attachAxis(self._growth_axis_x)
        self._growth_series.attachAxis(self._growth_axis_x)

        self._growth_axis_y = QValueAxis()
        self._growth_axis_y.setLabelFormat("%.1f")
        chart.addAxis(self._growth_axis_y, Qt.AlignLeft)
        self._growth_ci_area.attachAxis(self._growth_axis_y)
        self._growth_series.attachAxis(self._growth_axis_y)

        chart_view = QChartView(chart, parent)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_view.setStyleSheet("background-color: white; border: none;")

        return chart_view

    def _update_growth_chart(
        self,
        values: Sequence[float],
        ci_low: Sequence[float] | None = None,
        ci_high: Sequence[float] | None = None,
    ) -> None:
        if not self._growth_series:
            return

        points = [(float(index), value) for index, value in enumerate(values)]
        ci_points_low: list[tuple[float, float]] | None = None
        ci_points_high: list[tuple[float, float]] | None = None

        if (
            ci_low
            and ci_high
            and len(ci_low) == len(values)
            and len(ci_high) == len(values)
        ):
            ci_points_low = [(float(index), value) for index, value in enumerate(ci_low)]
            ci_points_high = [(float(index), value) for index, value in enumerate(ci_high)]

        combined_values: list[float] = list(values)
        if ci_low:
            combined_values.extend(ci_low)
        if ci_high:
            combined_values.extend(ci_high)

        self._update_growth_axis_range(combined_values)
        self._start_growth_animation(points, ci_points_low, ci_points_high)

    def _update_growth_axis_range(self, values: Sequence[float]) -> None:
        if not self._growth_axis_y:
            return

        if values:
            minimum = min(values)
            maximum = max(values)
            margin = max((maximum - minimum) * 0.1, 1.0)
            self._growth_axis_y.setRange(minimum - margin, maximum + margin)
            return

        self._growth_axis_y.setRange(0.0, 1.0)

    def _start_growth_animation(
        self,
        points: Sequence[tuple[float, float]],
        ci_low: Sequence[tuple[float, float]] | None = None,
        ci_high: Sequence[tuple[float, float]] | None = None,
    ) -> None:
        if not self._growth_series:
            return

        if self._growth_animation:
            self._growth_animation.stop()

        self._growth_animation_points = list(points)
        self._growth_ci_animation_points_low = list(ci_low or [])
        self._growth_ci_animation_points_high = list(ci_high or [])

        has_ci = bool(
            self._growth_ci_animation_points_low
            and self._growth_ci_animation_points_high
            and len(self._growth_ci_animation_points_low)
            == len(self._growth_ci_animation_points_high)
        )
        if self._growth_ci_area:
            self._growth_ci_area.setVisible(has_ci)
        if not has_ci:
            self._clear_ci_series()

        if not self._growth_animation_points:
            self._clear_growth_visuals()
            return

        if len(self._growth_animation_points) <= 1:
            final_points = [QPointF(x, y) for x, y in self._growth_animation_points]
            self._growth_series.replace(final_points)
            if has_ci:
                self._update_ci_series(
                    [QPointF(x, y) for x, y in self._growth_ci_animation_points_low],
                    [QPointF(x, y) for x, y in self._growth_ci_animation_points_high],
                )
            return

        if not self._growth_animation:
            self._growth_animation = QVariantAnimation(self)
            self._growth_animation.valueChanged.connect(self._handle_growth_animation_value)
            self._growth_animation.finished.connect(self._finalize_growth_animation)
            self._growth_animation.setEasingCurve(QEasingCurve.InOutCubic)

        self._growth_animation.setDuration(self._GROWTH_ANIMATION_DURATION_MS)
        self._growth_animation.setStartValue(0.0)
        self._growth_animation.setEndValue(float(len(self._growth_animation_points) - 1))
        self._growth_series.clear()
        if has_ci:
            self._clear_ci_series()
        self._growth_animation.start()

    def _handle_growth_animation_value(self, value: float) -> None:
        if not self._growth_series or not self._growth_animation_points:
            return

        animation_value = float(value)
        displayed_points = self._build_partial_points(
            self._growth_animation_points, animation_value
        )
        self._growth_series.replace(displayed_points)

        has_ci = bool(
            self._growth_ci_animation_points_low
            and self._growth_ci_animation_points_high
        )
        if not has_ci:
            return

        low_points = self._build_partial_points(
            self._growth_ci_animation_points_low, animation_value
        )
        high_points = self._build_partial_points(
            self._growth_ci_animation_points_high, animation_value
        )
        self._update_ci_series(low_points, high_points)

    def _finalize_growth_animation(self) -> None:
        if not self._growth_series or not self._growth_animation_points:
            return

        final_points = [QPointF(x, y) for x, y in self._growth_animation_points]
        self._growth_series.replace(final_points)

        has_ci = bool(
            self._growth_ci_animation_points_low
            and self._growth_ci_animation_points_high
        )
        if not has_ci:
            return

        self._update_ci_series(
            [QPointF(x, y) for x, y in self._growth_ci_animation_points_low],
            [QPointF(x, y) for x, y in self._growth_ci_animation_points_high],
        )

    def _clear_growth_visuals(self) -> None:
        if self._growth_series:
            self._growth_series.clear()
        self._clear_ci_series()

    def _clear_ci_series(self) -> None:
        if self._growth_ci_upper_series:
            self._growth_ci_upper_series.clear()
        if self._growth_ci_lower_series:
            self._growth_ci_lower_series.clear()
        if self._growth_ci_area:
            self._growth_ci_area.setVisible(False)

    def _update_ci_series(
        self,
        low_points: Sequence[QPointF],
        high_points: Sequence[QPointF],
    ) -> None:
        if not self._growth_ci_upper_series or not self._growth_ci_lower_series:
            return

        self._growth_ci_lower_series.replace(list(low_points))
        self._growth_ci_upper_series.replace(list(high_points))
        if self._growth_ci_area:
            self._growth_ci_area.setVisible(True)

    def _build_partial_points(
        self,
        source_points: Sequence[tuple[float, float]],
        animation_value: float,
    ) -> list[QPointF]:
        if not source_points:
            return []

        segment_index = int(animation_value)
        max_index = len(source_points) - 1
        segment_index = max(0, min(segment_index, max_index))

        displayed_points: list[QPointF] = []
        for idx in range(min(segment_index + 1, len(source_points))):
            x, y = source_points[idx]
            displayed_points.append(QPointF(x, y))

        next_index = segment_index + 1
        if next_index < len(source_points):
            start_x, start_y = source_points[segment_index]
            end_x, end_y = source_points[next_index]
            local_progress = animation_value - float(segment_index)
            interpolated_x = start_x + (end_x - start_x) * local_progress
            interpolated_y = start_y + (end_y - start_y) * local_progress
            displayed_points.append(QPointF(interpolated_x, interpolated_y))

        return displayed_points

    def _recalculate_growth_data(self) -> None:
        if not self._growth_table:
            return

        if not self._patient_data:
            self._set_growth_table_values(())
            self._update_growth_chart((), (), ())
            return

        mean_values, ci_low, ci_high = regression_V_no_treatment_with_ci(
            self._patient_data
        )
        self._set_growth_table_values(mean_values)
        self._update_growth_chart(mean_values, ci_low, ci_high)

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
        if self._molecular_subtype_value_label:
            self._molecular_subtype_value_label.setText("—")

        if not self._patient_data:
            self._patient_details_widget.hide()
            self._patient_placeholder_label.show()
            if self._edit_patient_button:
                self._edit_patient_button.setEnabled(False)
            self._recalculate_growth_data()
            self._log_therapy_recommendations()
            return

        for label, value in self._patient_data.items():
            name_label = QLabel(label, self._patient_details_widget)
            name_label.setWordWrap(True)
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            name_label.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Minimum,
            )
            value_label = QLabel(value or "—", self._patient_details_widget)
            value_label.setStyleSheet("font-weight: 600;")
            value_label.setWordWrap(True)
            value_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self._patient_details_form.addRow(name_label, value_label)

        stage_value = calculate_stage(self._patient_data)
        if self._stage_value_label:
            self._stage_value_label.setText(stage_value)

        subtype_value = self._calculate_molecular_subtype()
        if self._molecular_subtype_value_label:
            self._molecular_subtype_value_label.setText(subtype_value)

        self._patient_placeholder_label.hide()
        self._patient_details_widget.show()
        if self._edit_patient_button:
            self._edit_patient_button.setEnabled(True)
        self._recalculate_growth_data()
        self._log_therapy_recommendations()

    def _calculate_molecular_subtype(self) -> str:
        if not self._patient_data:
            return "—"

        er_status = self._interpret_marker_status(self._patient_data.get("Рецептор эстрогена", ""))
        pr_status = self._interpret_marker_status(self._patient_data.get("Рецептор прогестерона", ""))
        her2_status = self._interpret_marker_status(self._patient_data.get("HER2", ""))
        ki67_value = self._parse_percentage(self._patient_data.get("Уровень Ki-67 (%)", ""))

        pr_low = self._is_low_progesterone(self._patient_data.get("Рецептор прогестерона", ""), pr_status)
        ki67_low = ki67_value is not None and ki67_value <= 20
        ki67_high = ki67_value is not None and ki67_value >= 30

        if er_status is True and her2_status is False:
            if ki67_low and pr_status is True:
                return "Люминальный А"
            if ki67_high or pr_low:
                return "Люминальный B (HER2-отрицательный)"

        if er_status is True and her2_status is True:
            return "Люминальный B (HER2-положительный)"

        if her2_status is True and er_status is False and pr_status is False:
            return "HER2-положительный (не люминальный)"

        if her2_status is False and er_status is False and pr_status is False:
            return "Базальноподобный"

        return "—"

    @staticmethod
    def _interpret_marker_status(value: str | None) -> bool | None:
        if not value:
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None

        positive_tokens = {"+", "полож", "positive", "да"}
        negative_tokens = {"-", "отриц", "negative", "нет"}

        for token in positive_tokens:
            if normalized.startswith(token):
                return True
        for token in negative_tokens:
            if normalized.startswith(token):
                return False
        return None

    @staticmethod
    def _parse_percentage(value: str | None) -> float | None:
        if not value:
            return None

        match = re.search(r"(\d+[\.,]?\d*)", value.replace("%", ""))
        if not match:
            return None

        number = match.group(1).replace(",", ".")
        try:
            return float(number)
        except ValueError:
            return None

    @staticmethod
    def _is_low_progesterone(value: str | None, status: bool | None) -> bool:
        percentage = MainWindow._parse_percentage(value or "")
        if percentage is not None:
            return percentage < 20
        return status is False

    def _log_therapy_recommendations(self) -> None:
        if not self._patient_data:
            self._update_therapy_text(
                "<p>Недостаточно данных для расчёта рекомендаций. Заполните клинические параметры пациента.</p>"
            )
            return

        payload = self._build_therapy_payload()
        if not payload:
            self._update_therapy_text(
                "<p>Недостаточно данных для расчёта рекомендаций. Проверьте заполнение показателей T, N, M и статусов ER/PR/HER2.</p>"
            )
            return

        try:
            result = generate_treatment_recommendations(**payload)
        except Exception as error:
            self._update_therapy_text(
                f"<p>Ошибка при расчёте рекомендаций: {html.escape(str(error))}</p>"
            )
            return

        if not result:
            self._update_therapy_text("<p>Функция рекомендаций вернула пустой ответ.</p>")
            return

        formatted_result = format_therapy_recommendations(result)
        self._update_therapy_text(formatted_result)

    def _update_therapy_text(self, html_content: str) -> None:
        if not self._therapy_log_view:
            return

        content = html_content or "<p>Рекомендации пока недоступны.</p>"
        self._therapy_log_view.setHtml(content)

    def _build_therapy_payload(self) -> dict[str, object] | None:
        if not self._patient_data:
            return None

        er_status = self._interpret_marker_status(self._patient_data.get("Рецептор эстрогена", ""))
        pr_status = self._interpret_marker_status(self._patient_data.get("Рецептор прогестерона", ""))
        her2_status = self._interpret_marker_status(self._patient_data.get("HER2", ""))
        if er_status is None or pr_status is None or her2_status is None:
            return None

        t_category = normalize_category(self._patient_data.get("T", ""), "T")
        n_category = normalize_category(self._patient_data.get("N", ""), "N")
        m_category = normalize_category(self._patient_data.get("M", ""), "M")
        if not (t_category and n_category and m_category):
            return None

        menopausal_status = (self._patient_data.get("Менопаузальный статус") or "").strip().lower()
        if menopausal_status == "0" or not menopausal_status:
            menopausal_status = "premenopausal"
        allowed_statuses = {"premenopausal", "perimenopausal", "postmenopausal"}
        if menopausal_status not in allowed_statuses:
            menopausal_status = "premenopausal"

        ki67_value = self._parse_percentage(self._patient_data.get("Уровень Ki-67 (%)", ""))
        brca_status = self._interpret_marker_status(self._patient_data.get("Мутации в генах BRCA1/2", ""))
        e_cadherin = self._interpret_marker_status(self._patient_data.get("E-кадгерин", ""))
        if e_cadherin is True:
            e_cadherin_status: str | None = "positive"
        elif e_cadherin is False:
            e_cadherin_status = "negative"
        else:
            e_cadherin_status = None

        payload: dict[str, object] = {
            "age": calculate_age(self._patient_data.get("Дата рождения")) or 0,
            "gender": self._normalize_gender_value(self._patient_data.get("Пол пациента")),
            "menopausal_status": menopausal_status,
            "ER": er_status,
            "PR": pr_status,
            "HER2": her2_status,
            "BRCA_status": brca_status,
            "Ki67": ki67_value,
            "T": t_category,
            "grade": self._parse_grade_value(
                self._patient_data.get("Гистологическая градация опухоли (1-3)", "")
            ),
            "N": n_category,
            "M": m_category,
            "e_cadherin_status": e_cadherin_status,
            "surgery": False,
        }
        return payload

    @staticmethod
    def _normalize_gender_value(value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized.startswith("м"):
            return "male"
        if normalized.startswith("ж"):
            return "female"
        return "female"

    @staticmethod
    def _parse_grade_value(value: str | None) -> int:
        if not value:
            return 2
        cleaned = value.replace(",", ".").strip()
        try:
            numeric = float(cleaned)
        except ValueError:
            return 2
        integer_grade = int(round(numeric))
        return max(1, min(integer_grade, 3))

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
