"""Utility regressions for tumor volume estimations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final
import re

from core.patient_features import calculate_age, calculate_stage

try:  # pragma: no cover - optional dependency during development
    import joblib  # type: ignore
    import numpy as np
    import pandas as pd
except Exception:  # pragma: no cover - fallback when scientific stack is missing
    joblib = None
    np = None
    pd = None

_MODEL_FILENAME: Final = "gpr_notreatment_reduced_optuna.joblib"
_MODEL_PATH: Final = Path(__file__).resolve().parent.parent / "resources" / "models" / _MODEL_FILENAME
_TIME_POINTS_MONTHS: Final = (3, 6, 12, 24)
_FEATURE_COLUMNS: Final = (
    "stage",
    "age",
    "menopausal_status",
    "er_status",
    "pr_status",
    "her2_status",
    "brca_mutation",
    "ki67_level",
    "tumor_size_before",
)

if joblib is not None:  # pragma: no branch - executed when scientific stack available
    try:
        _GPR_MODEL = joblib.load(_MODEL_PATH)
    except Exception:  # pragma: no cover - I/O or deserialization failure
        _GPR_MODEL = None
else:  # pragma: no cover - executed when joblib is missing
    _GPR_MODEL = None


def regression_V_no_treatment(patient_data: Mapping[str, str] | None = None) -> list[float]:
    """Predict tumor size evolution at predefined horizons."""

    features = _prepare_model_features(patient_data)
    if not features:
        return _zero_growth_values()

    predictions = _predict_growth(features)
    if predictions is None:
        return _zero_growth_values()

    values = [features["tumor_size_before"], *predictions]
    return [round(value, 2) for value in values]


def _prepare_model_features(patient_data: Mapping[str, str] | None) -> dict[str, float | str] | None:
    if not patient_data:
        return None

    stage = calculate_stage(patient_data)
    if not stage or stage == "—":
        return None

    age = calculate_age(patient_data.get("Дата рождения"))
    menopausal_status = (patient_data.get("Менопаузальный статус", "") or "").strip().lower()
    er_status = _clean_marker(patient_data.get("Рецептор эстрогена"))
    pr_status = _clean_marker(patient_data.get("Рецептор прогестерона"))
    her2_status = _clean_marker(patient_data.get("HER2"))
    brca_status = _clean_marker(patient_data.get("Мутации в генах BRCA1/2"))
    ki67_level = _parse_numeric_value(patient_data.get("Уровень Ki-67 (%)"))
    tumor_size = _parse_numeric_value(patient_data.get("Размер опухоли до лечения (см)"))

    if (
        age is None
        or not menopausal_status
        or er_status is None
        or pr_status is None
        or her2_status is None
        or brca_status is None
        or ki67_level is None
        or tumor_size is None
    ):
        return None

    return {
        "stage": stage,
        "age": float(age),
        "menopausal_status": menopausal_status,
        "er_status": er_status,
        "pr_status": pr_status,
        "her2_status": her2_status,
        "brca_mutation": brca_status,
        "ki67_level": float(ki67_level),
        "tumor_size_before": float(tumor_size),
    }


def _predict_growth(features: Mapping[str, float | str]) -> list[float] | None:
    if not _GPR_MODEL or np is None or pd is None:
        return None

    try:
        frame = pd.DataFrame([features], columns=_FEATURE_COLUMNS)
        y_pred_log = _GPR_MODEL.predict(frame)
    except Exception:  # pragma: no cover - prediction failure
        return None

    if y_pred_log is None or len(y_pred_log) == 0:
        return None

    baseline = float(features["tumor_size_before"])
    ratios = np.exp(y_pred_log[0])
    return [float(baseline * ratio) for ratio in ratios]


def _parse_numeric_value(value: str | None) -> float | None:
    if not value:
        return None

    normalized = value.replace("%", "").strip()
    match = re.search(r"([-+]?\d+[\.,]?\d*)", normalized)
    if not match:
        return None

    number = match.group(1).replace(",", ".")
    try:
        parsed = float(number)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _clean_marker(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def _zero_growth_values() -> list[float]:
    return [0.0] * (len(_TIME_POINTS_MONTHS) + 1)
