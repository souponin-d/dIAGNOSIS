"""Chemotherapy response simulation utilities.

This module exposes a light-weight implementation of the algorithm
originally prototyped in a research notebook.  It accepts five tumor
volume measurements (baseline, 3, 6, 12 and 24 months) and produces two
sets of time series suitable for charting:

* Базовый сценарий, когда лечение не меняется.
* Сценарий с усилением терапии в точке минимального объёма.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

try:  # pragma: no cover - SciPy is an optional dependency during tests
    from scipy.optimize import curve_fit
    _SCIPY_STATUS = "SciPy найден: scipy.optimize.curve_fit доступен"
except Exception:  # pragma: no cover - keep the app functional without SciPy
    curve_fit = None  # type: ignore[assignment]
    _SCIPY_STATUS = "SciPy недоступен: scipy.optimize.curve_fit не найден"

_TIME_POINTS = np.array([0.0, 3.0, 6.0, 12.0, 24.0], dtype=float)
_DEFAULT_DT = 0.05
_SWITCH_BETA_MULTIPLIER = 4.0
_SWITCH_GAMMA_MULTIPLIER = 2.0


def _debug_print(message: str, *, payload: dict | None = None) -> None:
    """Emit verbose debug output for the chemotherapy pipeline."""

    prefix = "[ChemotherapyDebug] "
    if payload:
        print(f"{prefix}{message}: {payload}")
    else:
        print(f"{prefix}{message}")


_debug_print(_SCIPY_STATUS)


@dataclass(slots=True)
class ChemotherapySeries:
    """Container holding all tumor compartments for one scenario."""

    total: list[tuple[float, float]]
    sensitive: list[tuple[float, float]]
    tolerant: list[tuple[float, float]]
    resistant: list[tuple[float, float]]

    def to_mapping(self) -> dict[str, list[tuple[float, float]]]:
        return {
            "total": list(self.total),
            "sensitive": list(self.sensitive),
            "tolerant": list(self.tolerant),
            "resistant": list(self.resistant),
        }


@dataclass(slots=True)
class ChemotherapySimulationResult:
    """Full response description for both baseline and switch scenarios."""

    baseline: ChemotherapySeries
    adjusted: ChemotherapySeries
    switch_time: float | None


def generate_chemotherapy_forecast(
    values: Sequence[float],
    *,
    dt: float = _DEFAULT_DT,
) -> ChemotherapySimulationResult | None:
    """Fit the S–T–R model to five tumor measurements and build curves.

    Parameters
    ----------
    values:
        Iterable of five tumor volume values (baseline, 3, 6, 12, 24 months).
    dt:
        Integration step for the compartment model. Smaller values increase
        precision at the cost of performance.
    """

    _debug_print("Старт генерации прогноза", payload={"dt": dt, "values": list(values)})

    if curve_fit is None:
        _debug_print("Невозможно построить прогноз без SciPy")
        _log_final_result(None)
        return None

    measurements = _prepare_measurements(values)
    if measurements is None:
        _debug_print("Не удалось подготовить измерения")
        _log_final_result(None)
        return None

    _debug_print(
        "Подготовленные измерения",
        payload={"measurements": measurements.tolist()},
    )

    V0 = float(measurements[0])
    K = float(np.max(measurements) * 1.4 + 1e-3)
    r = _estimate_proliferation_rate(measurements)

    _debug_print("Оценённые параметры роста", payload={"V0": V0, "K": K, "r": r})

    def model_for_fit(t_points, beta_kill, gamma, alpha, mu):
        return _model_for_fit(
            t_points,
            beta_kill,
            gamma,
            alpha,
            mu,
            r=r,
            K=K,
            V0=V0,
            dt=dt,
        )

    try:
        popt, _ = curve_fit(
            model_for_fit,
            _TIME_POINTS,
            measurements,
            p0=[0.5, 0.1, 0.02, 0.02],
            bounds=([0.0, 0.0, 0.0, 0.0], [15.0, 10.0, 1.0, 1.0]),
            maxfev=20000,
        )
    except Exception as exc:  # pragma: no cover - numerical instability
        _debug_print("Сбой curve_fit", payload={"error": repr(exc)})
        _log_final_result(None)
        return None

    beta_kill, gamma, alpha, mu = map(float, popt)
    _debug_print(
        "Параметры после подбора",
        payload={
            "beta_kill": beta_kill,
            "gamma": gamma,
            "alpha": alpha,
            "mu": mu,
        },
    )

    baseline_series, switch_series, switch_time = _simulate_scenarios(
        beta_kill,
        gamma,
        alpha,
        mu,
        r=r,
        K=K,
        V0=V0,
        dt=dt,
    )

    result = ChemotherapySimulationResult(
        baseline=baseline_series,
        adjusted=switch_series,
        switch_time=switch_time,
    )
    _log_final_result(result)
    return result


def _log_final_result(result: ChemotherapySimulationResult | None) -> None:
    if result is None:
        _debug_print("Финальный результат: None")
        return
    _debug_print(
        "Финальный результат получен",
        payload={
            "baseline_points": len(result.baseline.total),
            "adjusted_points": len(result.adjusted.total),
            "switch_time": result.switch_time,
        },
    )


def _prepare_measurements(values: Sequence[float]) -> np.ndarray | None:
    if not values:
        _debug_print("Входные данные пустые")
        return None

    limited = list(values)[: len(_TIME_POINTS)]
    if len(limited) != len(_TIME_POINTS):
        _debug_print("Неправильное количество точек", payload={"expected": len(_TIME_POINTS), "got": len(limited)})
        return None

    try:
        measurements = np.array([float(value) for value in limited], dtype=float)
    except (TypeError, ValueError):  # pragma: no cover - invalid numbers
        _debug_print("Не удалось привести значения к float")
        return None

    if not np.all(np.isfinite(measurements)):
        _debug_print("Обнаружены нечисловые значения")
        return None

    return np.clip(measurements, 1e-6, None)


def _estimate_proliferation_rate(values: np.ndarray) -> float:
    safe = np.clip(values, 1e-6, None)
    logs = np.log(safe)
    slopes = np.diff(logs) / np.diff(_TIME_POINTS)
    slopes = slopes[np.isfinite(slopes)]
    if slopes.size == 0:
        _debug_print("Невозможно оценить темп роста, используем дефолт 0.05")
        return 0.05
    rate = float(np.clip(np.mean(slopes), 0.01, 0.5))
    _debug_print("Средний темп роста", payload={"rate": rate})
    return rate


def _model_for_fit(
    t_points: np.ndarray,
    beta_kill: float,
    gamma: float,
    alpha: float,
    mu: float,
    *,
    r: float,
    K: float,
    V0: float,
    dt: float,
) -> np.ndarray:
    t_end = float(np.max(t_points))
    T, _, _, _, Ntot = simulate_three_compartments(
        t_end,
        beta_kill=beta_kill,
        gamma=gamma,
        r=r,
        K=K,
        V0=V0,
        alpha=alpha,
        mu=mu,
        dt=dt,
    )
    return np.interp(t_points, T, Ntot)


def _simulate_scenarios(
    beta_kill: float,
    gamma: float,
    alpha: float,
    mu: float,
    *,
    r: float,
    K: float,
    V0: float,
    dt: float,
) -> tuple[ChemotherapySeries, ChemotherapySeries, float | None]:
    _debug_print(
        "Запуск симуляции базового сценария",
        payload={
            "beta_kill": beta_kill,
            "gamma": gamma,
            "alpha": alpha,
            "mu": mu,
            "r": r,
            "K": K,
            "V0": V0,
            "dt": dt,
        },
    )
    T, S, TOL, R, N = simulate_three_compartments(
        _TIME_POINTS[-1],
        beta_kill=beta_kill,
        gamma=gamma,
        r=r,
        K=K,
        V0=V0,
        alpha=alpha,
        mu=mu,
        dt=dt,
    )
    baseline_series = _create_series(T, S, TOL, R, N)

    _debug_print(
        "Получены ряды базового сценария",
        payload={"points": len(baseline_series.total)},
    )

    idx_min = int(np.argmin(N))
    if idx_min >= len(T) - 1:
        _debug_print("Минимум достигнут в конце, сценарий переключения не нужен")
        return baseline_series, baseline_series, None

    switch_time = float(T[idx_min])
    S_min, TOL_min, R_min = S[idx_min], TOL[idx_min], R[idx_min]

    _debug_print(
        "Параметры точки переключения",
        payload={
            "switch_time": switch_time,
            "S": S_min,
            "TOL": TOL_min,
            "R": R_min,
        },
    )

    T_sw, S_sw, TOL_sw, R_sw, N_sw = simulate_three_compartments_segment(
        t_start=switch_time,
        t_end=_TIME_POINTS[-1],
        beta_kill=beta_kill * _SWITCH_BETA_MULTIPLIER,
        gamma=gamma * _SWITCH_GAMMA_MULTIPLIER,
        r=r,
        K=K,
        S0=S_min,
        T0=TOL_min,
        R0=R_min,
        alpha=alpha,
        mu=mu,
        dt=dt,
    )

    if len(T_sw) <= 1:
        _debug_print("Сегмент после переключения слишком короткий")
        return baseline_series, baseline_series, switch_time

    T_full = np.concatenate([T[: idx_min + 1], T_sw[1:]])
    S_full = np.concatenate([S[: idx_min + 1], S_sw[1:]])
    TOL_full = np.concatenate([TOL[: idx_min + 1], TOL_sw[1:]])
    R_full = np.concatenate([R[: idx_min + 1], R_sw[1:]])
    N_full = np.concatenate([N[: idx_min + 1], N_sw[1:]])

    switch_series = _create_series(T_full, S_full, TOL_full, R_full, N_full)
    _debug_print(
        "Получены ряды с усилением",
        payload={"points": len(switch_series.total), "switch_time": switch_time},
    )
    return baseline_series, switch_series, switch_time


def simulate_three_compartments(
    t_end: float,
    *,
    beta_kill: float,
    gamma: float,
    r: float,
    K: float,
    V0: float,
    alpha: float = 0.02,
    beta_back: float = 0.01,
    mu: float = 0.02,
    sense_S: float = 1.0,
    sense_T: float = 0.3,
    sense_R: float = 0.0,
    dt: float = _DEFAULT_DT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    T = np.arange(0.0, t_end + dt, dt)
    _debug_print(
        "Интеграция трехкомпартментной модели",
        payload={"steps": len(T), "t_end": t_end, "dt": dt},
    )

    S = np.zeros_like(T)
    TOL = np.zeros_like(T)
    R = np.zeros_like(T)
    Ntot = np.zeros_like(T)

    S[0] = V0 * 0.95
    TOL[0] = V0 * 0.0
    R[0] = V0 * 0.05
    Ntot[0] = V0

    for i in range(1, len(T)):
        t = T[i]
        kill = beta_kill * np.exp(-gamma * t)
        N_prev = Ntot[i - 1]

        dS = r * S[i - 1] * (1 - N_prev / K) - kill * S[i - 1] * sense_S - alpha * S[i - 1] + beta_back * TOL[i - 1]
        dT = alpha * S[i - 1] - beta_back * TOL[i - 1] - mu * TOL[i - 1] - kill * TOL[i - 1] * sense_T
        dR = r * R[i - 1] * (1 - N_prev / K) + mu * TOL[i - 1] - kill * R[i - 1] * sense_R

        S[i] = max(S[i - 1] + dS * dt, 0.0)
        TOL[i] = max(TOL[i - 1] + dT * dt, 0.0)
        R[i] = max(R[i - 1] + dR * dt, 0.0)
        Ntot[i] = S[i] + TOL[i] + R[i]

    return T, S, TOL, R, Ntot


def simulate_three_compartments_segment(
    *,
    t_start: float,
    t_end: float,
    beta_kill: float,
    gamma: float,
    r: float,
    K: float,
    S0: float,
    T0: float,
    R0: float,
    alpha: float = 0.02,
    beta_back: float = 0.01,
    mu: float = 0.02,
    sense_S: float = 0.6,
    sense_T: float = 0.1,
    sense_R: float = 0.1,
    dt: float = _DEFAULT_DT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    T = np.arange(t_start, t_end + dt, dt)
    _debug_print(
        "Интеграция сегмента",
        payload={
            "steps": len(T),
            "t_start": t_start,
            "t_end": t_end,
            "dt": dt,
        },
    )

    S = np.zeros_like(T)
    TOL = np.zeros_like(T)
    R = np.zeros_like(T)
    Ntot = np.zeros_like(T)

    S[0] = max(S0, 0.0)
    TOL[0] = max(T0, 0.0)
    R[0] = max(R0, 0.0)
    Ntot[0] = S[0] + TOL[0] + R[0]

    for i in range(1, len(T)):
        t = T[i]
        tau = t - t_start
        kill = beta_kill * np.exp(-gamma * tau)
        N_prev = Ntot[i - 1]

        dS = r * S[i - 1] * (1 - N_prev / K) - kill * S[i - 1] * sense_S - alpha * S[i - 1] + beta_back * TOL[i - 1]
        dT = alpha * S[i - 1] - beta_back * TOL[i - 1] - mu * TOL[i - 1] - kill * TOL[i - 1] * sense_T
        dR = r * R[i - 1] * (1 - N_prev / K) + mu * TOL[i - 1] - kill * R[i - 1] * sense_R

        S[i] = max(S[i - 1] + dS * dt, 0.0)
        TOL[i] = max(TOL[i - 1] + dT * dt, 0.0)
        R[i] = max(R[i - 1] + dR * dt, 0.0)
        Ntot[i] = S[i] + TOL[i] + R[i]

    return T, S, TOL, R, Ntot


def _create_series(
    T: np.ndarray,
    S: np.ndarray,
    TOL: np.ndarray,
    R: np.ndarray,
    N: np.ndarray,
) -> ChemotherapySeries:
    def _pack(x: np.ndarray, y: np.ndarray) -> list[tuple[float, float]]:
        return [(float(ix), float(iy)) for ix, iy in zip(x, y)]

    return ChemotherapySeries(
        total=_pack(T, N),
        sensitive=_pack(T, S),
        tolerant=_pack(T, TOL),
        resistant=_pack(T, R),
    )
