"""Widget used to display analysis results."""

from __future__ import annotations

from typing import Mapping

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class ResultsView(QWidget):
    """Simple view that shows analysis results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._title = QLabel("Результат анализа", self)
        self._content = QTextEdit(self)
        self._content.setReadOnly(True)
        self._content.setPlaceholderText("Результат будет здесь")

        layout = QVBoxLayout()
        layout.addWidget(self._title)
        layout.addWidget(self._content)
        self.setLayout(layout)

    def show_result(self, result: Mapping[str, object]) -> None:
        """Render the provided result payload."""

        text_lines = [
            f"Риск: {result.get('risk_score', '—')}",
            f"Рекомендации: {result.get('recommendation', '—')}",
        ]
        details = result.get("details")
        if isinstance(details, Mapping) and details:
            text_lines.append("Дополнительные показатели:")
            for key, value in details.items():
                text_lines.append(f"  • {key}: {value}")
        self._content.setText("\n".join(text_lines))
