"""Stub analysis implementation."""

from __future__ import annotations

from core.models import AnalysisResult, PatientData


def analyze_patient(data: PatientData) -> AnalysisResult:
    """Analyze patient data and return a stubbed result."""

    recommendation = (
        "Пациенту рекомендуется дальнейшее наблюдение и повторный анализ через 3 месяца."
    )
    return AnalysisResult(risk_score=0.42, recommendation=recommendation, details={})
