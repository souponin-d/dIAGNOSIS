"""Background worker threads used by the UI."""

from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import QThread, Signal

from services.factory import AnalysisService


class AnalysisWorker(QThread):
    """Run analysis in a background thread."""

    finished = Signal(dict)
    errored = Signal(str)

    def __init__(self, service: AnalysisService, patient_payload: Dict[str, Any]) -> None:
        super().__init__()
        self._service = service
        self._payload = patient_payload

    def run(self) -> None:  # type: ignore[override]
        """Execute the analysis in a thread-safe context."""

        try:
            result = self._service.analyze(self._payload)
        except Exception as exc:  # pragma: no cover - UI feedback
            self.errored.emit(str(exc))
        else:
            self.finished.emit(result)
