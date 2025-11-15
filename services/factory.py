"""Factory for obtaining analysis services."""

from __future__ import annotations

from typing import Protocol

from config import AppConfig
from services.analysis_http import HttpAnalysisService
from services.analysis_local import LocalAnalysisService


class AnalysisService(Protocol):
    """Protocol describing analysis service implementations."""

    def analyze(self, patient_payload: dict) -> dict:
        """Trigger analysis and return a dictionary result."""


def get_analysis_service(config: AppConfig) -> AnalysisService:
    """Return the appropriate analysis service based on configuration."""

    if config.analysis_mode == "local":
        return LocalAnalysisService()
    if config.analysis_mode == "http":
        return HttpAnalysisService(config.backend_base_url)
    raise ValueError(f"Unknown analysis mode: {config.analysis_mode}")
