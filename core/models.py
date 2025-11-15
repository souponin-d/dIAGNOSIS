"""Data models for analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping


@dataclass(slots=True)
class PatientData:
    """Represents patient information used for analysis."""

    age: int
    sex: str
    lab_results: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class AnalysisResult:
    """Represents the outcome of an analysis."""

    risk_score: float
    recommendation: str
    details: Dict[str, float] = field(default_factory=dict)
