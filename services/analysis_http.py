"""HTTP analysis service placeholder."""

from __future__ import annotations

from typing import Any, Dict


class HttpAnalysisService:
    """Stub HTTP-based analysis service."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def analyze(self, patient_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder HTTP analysis call."""

        raise NotImplementedError("HTTP analysis service is not implemented yet.")
