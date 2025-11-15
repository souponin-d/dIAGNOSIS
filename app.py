"""Application bootstrap module."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from config import CONFIG
from ui.main_window import MainWindow
from utils.logging_config import setup_logging


def create_main_window(app: QApplication | None = None) -> MainWindow:
    """Create and initialize the main window."""

    setup_logging(CONFIG.log_level)
    window = MainWindow(config=CONFIG, application=app)
    return window
