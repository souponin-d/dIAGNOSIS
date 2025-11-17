"""Utility regressions for tumor volume estimations."""

from __future__ import annotations

from collections.abc import Mapping


def regression_V_no_treatment(patient_data: Mapping[str, str] | None = None) -> list[float]:
    """Estimate tumor volume progression without treatment.

    The implementation is intentionally simple and serves as a placeholder so
    that the UI can al  ready consume structured data. Once the actual
    statistical model is available, it can replace the internals of this
    function without affecting the rest of the application.
    """

    if not patient_data:
        return []

    tumor_size_raw = patient_data.get("Размер опухоли до лечения (см)", "0") or "0"
    try:
        baseline = float(str(tumor_size_raw).replace(",", "."))
    except ValueError:
        baseline = 0.0

    # Simulate unchecked growth without treatment.
    growth_coefficients = (0.0, 0.15, 0.35, 0.65, 1.0)
    return [round(baseline * (1 + coef), 2) for coef in growth_coefficients]
