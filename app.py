"""Application bootstrap module."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from config import CONFIG
from ui.main_window import MainWindow
from utils.logging_config import setup_logging


def create_main_window(app: QApplication | None = None) -> MainWindow:
    """Create and initialize the main window."""

    setup_logging(CONFIG.log_level)

    if app is not None:
        _apply_application_font(app)

    window = MainWindow(config=CONFIG, application=app)
    return window


def _apply_application_font(app: QApplication) -> None:
    """Load the Montserrat font from resources and apply it to the app."""

    font_path = Path(__file__).resolve().parent / "resources" / "fonts" / "Montserrat.ttf"
    if not font_path.exists():
        return

    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        return

    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        return

    current_font = app.font()
    new_font = QFont(families[0], current_font.pointSize())
    new_font.setStyle(current_font.style())
    new_font.setWeight(current_font.weight())
    app.setFont(new_font)
