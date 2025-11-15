"""Local analysis service implementation."""

from __future__ import annotations

from typing import Any, Dict

from core.analysis import analyze_patient
from core.models import AnalysisResult, PatientData


class LocalAnalysisService:
    """Service that delegates analysis to the local core logic."""

    def analyze(self, patient_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis using the local Python implementation."""

        data = PatientData(
            age=int(patient_payload.get("age", 0)),
            sex=str(patient_payload.get("sex", "unknown")),
            lab_results=patient_payload.get("lab_results", {}),
        )
        result: AnalysisResult = analyze_patient(data)
        return {
            "risk_score": result.risk_score,
            "recommendation": result.recommendation,
            "details": result.details,
        }
