"""Entry point for the desktop application."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app import create_main_window


def main() -> None:
    """Run the Qt event loop."""

    application = QApplication(sys.argv)
    window = create_main_window(application)
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
