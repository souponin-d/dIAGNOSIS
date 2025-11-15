"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from config import AppConfig
from ui.dialogs.create_patient_dialog import CreatePatientDialog


class MainWindow(QMainWindow):
    """Primary window displaying the start screen with background and menu."""

    _BACKGROUND_PATH = Path(__file__).resolve().parents[1] / "resources" / "images" / "background.png"

    def __init__(self, config: AppConfig, application: Optional[QApplication] = None) -> None:
        super().__init__()
        self._config = config
        self._application = application

        self.setWindowTitle("dIAGNOSIS")
        self.setFixedSize(1920, 1080)

        self._background_label: QLabel | None = None

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
            self._background_label.setPixmap(pixmap)

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

        menu_bar.addMenu("Помощь")

    def _open_create_dialog(self) -> None:
        dialog = CreatePatientDialog(self)
        dialog.exec()
