"""Utility regressions for tumor volume estimations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final
import logging
import re
import warnings

from core.patient_features import calculate_age, calculate_stage

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False

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
_CONFIDENCE_Z_SCORE: Final = 1.96
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
_ROMAN_STAGE_VALUES: Final = {
    "0": 0.0,
    "I": 1.0,
    "II": 2.0,
    "III": 3.0,
    "IV": 4.0,
}

if joblib is not None:  # pragma: no branch - executed when scientific stack available
    try:
        _GPR_MODEL = joblib.load(_MODEL_PATH)
        logger.debug("[regression] Gaussian Process model loaded from %s.", _MODEL_PATH)
    except Exception as error:  # pragma: no cover - I/O or deserialization failure
        logger.debug("[regression] Failed to load model: %s", error)
        _GPR_MODEL = None
else:  # pragma: no cover - executed when joblib is missing
    logger.debug("[regression] Scientific stack is unavailable; predictions will be disabled.")
    _GPR_MODEL = None


def regression_V_no_treatment(patient_data: Mapping[str, str] | None = None) -> list[float]:
    """Predict tumor size evolution at predefined horizons."""

    mean_values, _, _ = regression_V_no_treatment_with_ci(patient_data)
    return [round(value, 2) for value in mean_values]


def regression_V_no_treatment_with_ci(
    patient_data: Mapping[str, str] | None = None,
) -> tuple[list[float], list[float], list[float]]:
    """Predict tumor size evolution along with confidence intervals."""

    logger.debug("[regression] Starting tumor growth estimation.")
    features = _prepare_model_features(patient_data)
    if not features:
        logger.debug("[regression] Not enough structured features; returning zeros.")
        return _zero_growth_interval_values()

    logger.debug("[regression] Prepared features: %s", features)
    interval_predictions = _predict_growth_with_uncertainty(features)
    if interval_predictions is None:
        logger.debug("[regression] Falling back to point predictions only.")
        point_predictions = _predict_growth(features)
        if point_predictions is None:
            logger.debug("[regression] Prediction step failed; returning zeros.")
            return _zero_growth_interval_values()
        mean_predictions = point_predictions
        low_predictions = point_predictions
        high_predictions = point_predictions
    else:
        mean_predictions, low_predictions, high_predictions = interval_predictions

    baseline = float(features["tumor_size_before"])
    mean_values = [baseline, *mean_predictions]
    low_values = [baseline, *low_predictions]
    high_values = [baseline, *high_predictions]
    logger.debug("[regression] Final growth curve (mean): %s", mean_values)
    logger.debug("[regression] Confidence interval low: %s", low_values)
    logger.debug("[regression] Confidence interval high: %s", high_values)
    return mean_values, low_values, high_values


def _prepare_model_features(patient_data: Mapping[str, str] | None) -> dict[str, float | str] | None:
    if not patient_data:
        return None

    stage = calculate_stage(patient_data)
    stage_numeric = _convert_stage_to_numeric(stage)
    if stage_numeric is None:
        return None

    age = calculate_age(patient_data.get("Дата рождения"))
    menopausal_status = (patient_data.get("Менопаузальный статус", "") or "").strip().lower()
    er_status = _parse_marker_status(patient_data.get("Рецептор эстрогена"))
    pr_status = _parse_marker_status(patient_data.get("Рецептор прогестерона"))
    her2_status = _parse_marker_status(patient_data.get("HER2"))
    brca_status = _parse_marker_status(patient_data.get("Мутации в генах BRCA1/2"))
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
        "stage": stage_numeric,
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
        logger.debug("[regression] Model or dependencies are unavailable.")
        return None

    try:
        logger.debug("[regression] Running inference through the Gaussian Process model.")
        frame = pd.DataFrame([features], columns=_FEATURE_COLUMNS)
        y_pred_log = _GPR_MODEL.predict(frame)
    except Exception as error:  # pragma: no cover - prediction failure
        logger.debug("[regression] Prediction error: %s", error)
        return None

    if y_pred_log is None or len(y_pred_log) == 0:
        logger.debug("[regression] Model returned no predictions.")
        return None

    baseline = float(features["tumor_size_before"])
    ratios = np.exp(y_pred_log[0])
    logger.debug("[regression] Model raw output (log-space): %s", y_pred_log)
    return [float(baseline * ratio) for ratio in ratios]


def _predict_growth_with_uncertainty(
    features: Mapping[str, float | str],
    z_value: float = _CONFIDENCE_Z_SCORE,
) -> tuple[list[float], list[float], list[float]] | None:
    if not _GPR_MODEL or np is None or pd is None:
        logger.debug("[regression] Model or dependencies are unavailable.")
        return None

    try:
        frame = pd.DataFrame([features], columns=_FEATURE_COLUMNS)
        prep = _GPR_MODEL.named_steps["prep"]
        gpr_multi = _GPR_MODEL.named_steps["gpr"]
    except Exception as error:  # pragma: no cover - unexpected pipeline layout
        logger.debug("[regression] Pipeline structure unexpected: %s", error)
        return None

    try:
        transformed = prep.transform(frame)
    except Exception as error:  # pragma: no cover - preprocessing failure
        logger.debug("[regression] Preprocessing failed: %s", error)
        return None

    means: list[float] = []
    stds: list[float] = []
    try:
        for estimator in gpr_multi.estimators_:
            mu, sigma = estimator.predict(transformed, return_std=True)
            means.append(float(mu[0]))
            stds.append(float(sigma[0]))
    except Exception as error:  # pragma: no cover - prediction failure
        logger.debug("[regression] Failed to obtain uncertainty estimates: %s", error)
        return None

    mean_array = np.array(means)
    std_array = np.array(stds)
    ratios_mean = np.exp(mean_array)
    ratios_low = np.exp(mean_array - z_value * std_array)
    ratios_high = np.exp(mean_array + z_value * std_array)
    baseline = float(features["tumor_size_before"])
    return (
        [float(baseline * ratio) for ratio in ratios_mean],
        [float(baseline * ratio) for ratio in ratios_low],
        [float(baseline * ratio) for ratio in ratios_high],
    )


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


def _convert_stage_to_numeric(stage: str | None) -> float | None:
    if not stage:
        return None

    cleaned = stage.strip().upper()
    if not cleaned or cleaned == "—":
        return None

    for prefix in ("IV", "III", "II", "I", "0"):
        if cleaned.startswith(prefix):
            return _ROMAN_STAGE_VALUES.get(prefix)
    return None


def _parse_marker_status(value: str | None) -> bool | None:
    if not value:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    leading_token = normalized.split()[0]
    if leading_token.startswith("+"):
        return True
    if leading_token.startswith("-"):
        return False

    if "+" in normalized and "-" not in normalized:
        return True
    if "-" in normalized and "+" not in normalized:
        return False

    if normalized.startswith(("pos", "полож")):
        return True
    if normalized.startswith(("neg", "отр")):
        return False

    return None


def _zero_growth_values() -> list[float]:
    return [0.0] * (len(_TIME_POINTS_MONTHS) + 1)


def _zero_growth_interval_values() -> tuple[list[float], list[float], list[float]]:
    zeros = _zero_growth_values()
    return zeros.copy(), zeros.copy(), zeros.copy()
