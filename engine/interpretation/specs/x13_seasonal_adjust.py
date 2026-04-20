"""
InterpretationSpec for x13_seasonal_adjust.

Distinct from STL/classical/MSTL: X-13 emits no trend-strength metric
but adds transform, outlier-detection, and backend diagnostics. Tier 1
leads with transform choice and seasonal strength. Tier 2 explicitly
discloses which backend was used (Census binary vs statsmodels
fallback) per Decision E — always full disclosure.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_RHO,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _strength_band(v: float) -> str:
    v = float(v)
    if v < 0.3:
        return "weak"
    if v < 0.6:
        return "moderate"
    if v < 0.9:
        return "strong"
    return "very strong"


def _backend_clause(backend: str) -> str:
    b = str(backend or "").lower()
    if "census" in b or "binary" in b or "x13as" in b:
        return "X-13 backend = Census Bureau binary"
    if "statsmodels" in b or "fallback" in b:
        return "X-13 backend = statsmodels fallback (Census binary unavailable)"
    return f"X-13 backend = {backend}"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    period = int(results.get("period", 0))
    Fs = float(results.get("seasonal_strength", 0.0))
    transform = str(results.get("transform", "none"))
    outlier = bool(results.get("outlier_detection", False))
    freq_word = "monthly" if period == 12 else "quarterly" if period == 4 else f"period-{period}"
    transform_clause = f"{transform} transform applied"
    if transform == "none":
        transform_clause = "no transform applied"
    outlier_clause = "with outlier detection" if outlier else "without outlier detection"
    return (
        f"X-13ARIMA-SEATS seasonally-adjusted "
        f"{format_series_reference(name)} ({n} observations, "
        f"{freq_word}). {transform_clause.capitalize()} {outlier_clause}; "
        f"seasonal strength {FMT_RHO.format(Fs)} ({_strength_band(Fs)}). "
        f"The seasonally-adjusted series in the data tables isolates "
        f"the trend-cycle and irregular components for month-over-"
        f"month analysis."
    )


def _tier2(results: dict) -> str:
    backend = str(results.get("backend", "unknown"))
    n_outliers = int(results.get("n_outliers", 0) or 0)
    outlier_clause = (
        f"AO/LS outlier detection identified {n_outliers} events."
        if n_outliers > 0 else
        "No AO/LS outliers detected (or detection disabled)."
    )
    return (
        f"{_backend_clause(backend)}. {outlier_clause} Seasonal "
        f"strength computed as 1 − Var(I)/Var(S+I). Unlike classical/"
        f"STL, X-13 emits an irregular component separately from "
        f"residuals — useful for month-over-month noise attribution "
        f"under official-statistics conventions."
    )


def _trigger_fallback_in_use(results: dict) -> Optional[str]:
    backend = str(results.get("backend", "")).lower()
    if "fallback" not in backend and "statsmodels" not in backend:
        return None
    return (
        "X-13 results are from the statsmodels fallback path. Install "
        "the Census Bureau X-13 binary for production-grade seasonal "
        "adjustment consistent with official government statistical "
        "releases; fallback results may diverge on edge cases."
    )


def _trigger_negligible_seasonality(results: dict) -> Optional[str]:
    Fs = float(results.get("seasonal_strength", 0.0))
    if Fs >= 0.3:
        return None
    return (
        f"Seasonal strength {FMT_RHO.format(Fs)} is below 0.30; the "
        f"series may not require seasonal adjustment. Consider using "
        f"the original series or a simpler detrending approach."
    )


SPEC = InterpretationSpec(
    technique_id="x13_seasonal_adjust",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_fallback_in_use, _trigger_negligible_seasonality),
    mode_aware=False,
)

register(SPEC)
