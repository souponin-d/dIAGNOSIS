"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCharts import QChart, QChartView, QScatterSeries
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QMouseEvent, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QWIDGETSIZE_MAX,
)

from config import AppConfig
from ui.dialogs.create_patient_dialog import CreatePatientDialog


class MainWindow(QMainWindow):
    """Primary window displaying the start screen with background and menu."""

    _BACKGROUND_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "background.png"
    _ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "logo.png"
    _MENU_EXPANDED_WIDTH = 240
    _WINDOW_RADIUS = 40
    _ILLUSTRATION_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "logo.png"

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
        self.setFixedSize(self.size())

        self._background_label: QLabel | None = None
        self._background_pixmap: QPixmap | None = None
        self._menu_widget: QWidget | None = None
        self._content_widget: QWidget | None = None
        self._menu_animation: QPropertyAnimation | None = None
        self._menu_expanded = False
        self._menu_toggle_button: QToolButton | None = None
        self._tab_widget: QTabWidget | None = None
        self._section_pages: dict[str, QWidget] = {}
        self._startup_view = True
        self._drag_position: QPoint | None = None
        self._illustration_label: QLabel | None = None

        self._init_ui()
        self._center_on_screen()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setContentsMargins(0, 0, 0, 0)
        central_widget.setAttribute(Qt.WA_StyledBackground, True)
        central_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(central_widget)

        self._background_label = QLabel(central_widget)
        self._background_label.setAlignment(Qt.AlignCenter)
        self._background_label.setContentsMargins(0, 0, 0, 0)
        self._background_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._background_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._background_label.lower()

        content_widget = QWidget(central_widget)
        content_widget.setObjectName("startupContent")
        content_widget.setAttribute(Qt.WA_StyledBackground, True)
        content_widget.setStyleSheet(
            "#startupContent { background-color: rgba(255, 255, 255, 235); border-radius: 40px; }"
        )

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(content_widget)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_widget.setLayout(content_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(24, 24, 24, 0)
        buttons_layout.setSpacing(12)
        buttons_layout.addStretch()

        create_button = QPushButton("Создать", content_widget)
        create_button.setCursor(Qt.PointingHandCursor)
        create_button.setFixedHeight(36)
        create_button.clicked.connect(self._open_create_dialog)
        buttons_layout.addWidget(create_button)

        close_button = QPushButton("Х", content_widget)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setFixedSize(36, 36)
        close_button.clicked.connect(self.close)
        buttons_layout.addWidget(close_button)

        content_layout.addLayout(buttons_layout)
        content_layout.addStretch()

        illustration_label = QLabel(content_widget)
        illustration_label.setAlignment(Qt.AlignCenter)
        illustration_label.setAttribute(Qt.WA_TranslucentBackground, True)
        illustration_pixmap = QPixmap(str(self._ILLUSTRATION_PATH))
        if not illustration_pixmap.isNull():
            illustration_label.setPixmap(
                illustration_pixmap.scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        content_layout.addWidget(illustration_label)
        self._illustration_label = illustration_label
        content_layout.addStretch()

        pixmap = QPixmap(str(self._BACKGROUND_PATH))
        if not pixmap.isNull():
            self._background_pixmap = pixmap
            self._update_background_pixmap()

        self.menuBar().hide()

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
        self._apply_window_mask()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_background_pixmap()
        self._apply_window_mask()

    def _open_create_dialog(self) -> None:
        dialog = CreatePatientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._transition_to_full_screen()

    def _update_background_pixmap(self) -> None:
        if not self._background_label:
            return

        if not self._background_pixmap or self._background_pixmap.isNull():
            return

        central_widget = self.centralWidget()
        if central_widget is None:
            return

        target_size = central_widget.size()
        if not target_size.isValid():
            return

        self._background_label.resize(target_size)
        self._background_label.move(0, 0)

        scaled_pixmap = self._background_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        if scaled_pixmap.size() != target_size:
            x_offset = max((scaled_pixmap.width() - target_size.width()) // 2, 0)
            y_offset = max((scaled_pixmap.height() - target_size.height()) // 2, 0)
            cropped_pixmap = scaled_pixmap.copy(
                x_offset,
                y_offset,
                target_size.width(),
                target_size.height(),
            )
        else:
            cropped_pixmap = scaled_pixmap

        self._background_label.setPixmap(cropped_pixmap)
        self._background_label.lower()

    def _apply_window_mask(self) -> None:
        if not self._startup_view:
            return

        rect = self.rect()
        if not rect.isValid():
            return

        device_ratio = self.devicePixelRatioF()
        if device_ratio <= 0:
            device_ratio = 1.0

        mask_size = QSize(int(rect.width() * device_ratio), int(rect.height() * device_ratio))
        if not mask_size.isValid():
            return

        mask_pixmap = QPixmap(mask_size)
        mask_pixmap.fill(Qt.transparent)

        painter = QPainter(mask_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        painter.scale(device_ratio, device_ratio)
        painter.drawRoundedRect(
            QRectF(0, 0, rect.width(), rect.height()), self._WINDOW_RADIUS, self._WINDOW_RADIUS
        )
        painter.end()

        mask_pixmap.setDevicePixelRatio(device_ratio)
        self.setMask(mask_pixmap.mask())

    def _transition_to_full_screen(self) -> None:
        if not self._startup_view:
            return

        if self._background_label:
            self._background_label.hide()
            self._background_label.deleteLater()
            self._background_label = None
            self._background_pixmap = None

        self._startup_view = False
        self.setMask(QRegion())
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
        project_widget.setStyleSheet("background-color: #ffffff;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        project_widget.setLayout(layout)

        self._menu_widget = QWidget(project_widget)
        self._menu_widget.setMinimumWidth(0)
        self._menu_widget.setMaximumWidth(0)
        self._menu_widget.setStyleSheet("background-color: #f1f1f1;")

        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(16, 32, 16, 16)
        menu_layout.setSpacing(12)
        self._menu_widget.setLayout(menu_layout)

        sections = ("Информация", "Терапия", "Прогноз")
        self._section_pages = {}

        for section in sections:
            section_button = QPushButton(section, self._menu_widget)
            section_button.setCursor(Qt.PointingHandCursor)
            section_button.setStyleSheet("text-align: left; padding: 8px 12px;")
            section_button.setFlat(True)
            section_button.clicked.connect(
                lambda _checked=False, name=section: self._activate_section(name)
            )
            menu_layout.addWidget(section_button)

        menu_layout.addStretch()

        layout.addWidget(self._menu_widget)

        self._content_widget = QWidget(project_widget)
        self._content_widget.setAttribute(Qt.WA_StyledBackground, True)
        self._content_widget.setStyleSheet("background-color: #ffffff;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        self._content_widget.setLayout(content_layout)

        layout.addWidget(self._content_widget, 1)

        self._menu_toggle_button = QToolButton(self._content_widget)
        self._menu_toggle_button.setText("☰")
        self._menu_toggle_button.setToolTip("Меню")
        self._menu_toggle_button.setCheckable(True)
        self._menu_toggle_button.setFixedSize(40, 40)
        self._menu_toggle_button.clicked.connect(self._toggle_menu)
        content_layout.addWidget(self._menu_toggle_button, alignment=Qt.AlignLeft)

        self._tab_widget = QTabWidget(self._content_widget)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setStyleSheet(
            "QTabWidget::pane { background: #ffffff; border: none; }"
        )
        if tab_bar := self._tab_widget.tabBar():
            tab_bar.hide()
        content_layout.addWidget(self._tab_widget, 1)

        info_tab = QWidget(self._tab_widget)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(16)
        info_tab.setLayout(info_layout)

        chart_view = self._create_information_chart()
        info_layout.addWidget(chart_view)

        self._tab_widget.addTab(info_tab, "Информация")
        self._section_pages["Информация"] = info_tab

        for section in sections[1:]:
            section_tab = QWidget(self._tab_widget)
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(16)
            section_label = QLabel("Раздел в разработке", section_tab)
            section_label.setAlignment(Qt.AlignCenter)
            section_label.setStyleSheet("font-size: 18px; color: #444;")
            section_layout.addStretch()
            section_layout.addWidget(section_label)
            section_layout.addStretch()
            section_tab.setLayout(section_layout)
            self._tab_widget.addTab(section_tab, section)
            self._section_pages[section] = section_tab

        self._menu_animation = QPropertyAnimation(self._menu_widget, b"maximumWidth", self)
        self._menu_animation.setDuration(250)
        self._menu_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._menu_expanded = False

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

    def _activate_section(self, section: str) -> None:
        if not self._tab_widget:
            return

        page = self._section_pages.get(section)
        if not page:
            return

        index = self._tab_widget.indexOf(page)
        if index != -1:
            self._tab_widget.setCurrentIndex(index)

    def _create_information_chart(self) -> QChartView:
        series = QScatterSeries()
        series.setMarkerSize(12.0)
        series.setColor(self.palette().highlight().color())

        points = (
            QPointF(0.0, 2.0),
            QPointF(1.0, 3.5),
            QPointF(2.0, 2.8),
            QPointF(3.0, 4.2),
            QPointF(4.0, 3.9),
            QPointF(5.0, 5.1),
            QPointF(6.0, 4.6),
            QPointF(7.0, 5.4),
        )

        for point in points:
            series.append(point)

        chart = QChart()
        chart.addSeries(series)
        chart.createDefaultAxes()
        chart.setTitle("Измеренные показатели")
        chart.legend().hide()
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_view.setStyleSheet("background-color: #ffffff; border: none;")

        return chart_view

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
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
