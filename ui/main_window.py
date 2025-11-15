"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import AppConfig
from ui.dialogs.create_patient_dialog import CreatePatientDialog


class MainWindow(QMainWindow):
    """Primary window displaying the start screen with background and menu."""

    _BACKGROUND_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "background.png"
    _ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "logo.png"
    _MENU_EXPANDED_WIDTH = 240

    def __init__(self, config: AppConfig, application: Optional[QApplication] = None) -> None:
        super().__init__()
        self._config = config
        self._application = application

        self.setWindowTitle("dIAGNOSIS")
        self.setWindowIcon(QIcon(str(self._ICON_PATH)))
        self.resize(720, 480)

        self._background_label: QLabel | None = None
        self._background_pixmap: QPixmap | None = None
        self._menu_widget: QWidget | None = None
        self._content_widget: QWidget | None = None
        self._menu_animation: QPropertyAnimation | None = None
        self._menu_expanded = False
        self._menu_toggle_button: QToolButton | None = None

        self._init_ui()
        self._create_menus()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        self._background_label = QLabel(self)
        self._background_label.setAlignment(Qt.AlignCenter)
        self._background_label.setContentsMargins(0, 0, 0, 0)

        pixmap = QPixmap(str(self._BACKGROUND_PATH))
        if not pixmap.isNull():
            self._background_pixmap = pixmap
            self._update_background_pixmap()

        layout.addWidget(self._background_label, alignment=Qt.AlignCenter)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

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

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_background_pixmap()

    def _open_create_dialog(self) -> None:
        dialog = CreatePatientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._transition_to_full_screen()

    def _update_background_pixmap(self) -> None:
        if not self._background_label or not self._background_label.isVisible():
            return

        if not self._background_pixmap or self._background_pixmap.isNull():
            return

        target_size = self.centralWidget().size()
        if not target_size.isValid():
            return

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

    def _transition_to_full_screen(self) -> None:
        if self._background_label:
            self._background_label.hide()
            layout = self.centralWidget().layout()
            if layout is not None:
                layout.removeWidget(self._background_label)
            self._background_label.deleteLater()
            self._background_label = None
            self._background_pixmap = None

        previous_central_widget = self.centralWidget()
        project_widget = QWidget(self)
        project_widget.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(project_widget)

        if previous_central_widget is not None:
            previous_central_widget.deleteLater()

        self._init_project_view(project_widget)
        self.showMaximized()

    def _init_project_view(self, project_widget: QWidget) -> None:
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

        for section in ("Информация", "Терапия", "Прогноз"):
            section_button = QPushButton(section, self._menu_widget)
            section_button.setCursor(Qt.PointingHandCursor)
            section_button.setStyleSheet("text-align: left; padding: 8px 12px;")
            section_button.setFlat(True)
            menu_layout.addWidget(section_button)

        menu_layout.addStretch()

        layout.addWidget(self._menu_widget)

        self._content_widget = QWidget(project_widget)
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

        content_layout.addStretch()

        placeholder_label = QLabel("Выберите раздел из меню", self._content_widget)
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 18px; color: #444;")
        content_layout.addWidget(placeholder_label, alignment=Qt.AlignCenter)

        content_layout.addStretch()

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
