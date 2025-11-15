"""Main application window."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from config import AppConfig
from services.factory import AnalysisService, get_analysis_service
from ui.dialogs.settings_dialog import SettingsDialog
from ui.widgets.patient_form import PatientForm
from ui.widgets.results_view import ResultsView
from ui.widgets.toolbar import MainToolbar
from ui.workers import AnalysisWorker


class MainWindow(QMainWindow):
    """Primary window coordinating UI and service interactions."""

    def __init__(self, config: AppConfig, application: Optional[QApplication] = None) -> None:
        super().__init__()
        self._config = config
        self._application = application
        self._analysis_service: AnalysisService = get_analysis_service(config)
        self._analysis_worker: Optional[AnalysisWorker] = None
        self._toolbar: Optional[MainToolbar] = None

        self.setWindowTitle("dIAGNOSIS")
        self.resize(900, 600)
        self._init_ui()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self._patient_form = PatientForm(self)
        self._results_view = ResultsView(self)

        layout = QHBoxLayout(central_widget)
        central_widget.setLayout(layout)
        layout.addWidget(self._patient_form, 1)
        layout.addWidget(self._results_view, 1)

        self._toolbar = MainToolbar(self)
        self._toolbar.settings_requested.connect(self.open_settings)
        self.addToolBar(Qt.TopToolBarArea, self._toolbar)
        self._patient_form.analyze_requested.connect(self._start_analysis)

    def _start_analysis(self, payload: dict) -> None:
        if self._analysis_worker is not None:
            self._analysis_worker.quit()
            self._analysis_worker.wait()

        self._analysis_worker = AnalysisWorker(self._analysis_service, payload)
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.errored.connect(self._on_analysis_error)
        self._analysis_worker.start()

    def _on_analysis_finished(self, result: dict) -> None:
        self._results_view.show_result(result)

    def _on_analysis_error(self, message: str) -> None:
        QMessageBox.warning(self, "Ошибка анализа", message)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self)
        dialog.exec()
