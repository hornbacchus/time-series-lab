"""
InterpretationSpec for stl_decompose.

Tier 1 leads with seasonal/trend strength and period. Tier 2 discloses
the Loess-based method and adaptive-seasonality advantage over classical.
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


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    period = int(results.get("period", 0))
    Fs = float(results.get("seasonal_strength", 0.0))
    Ft = float(results.get("trend_strength", 0.0))
    return (
        f"STL decomposition of {format_series_reference(name)} "
        f"({n} observations, period {period}). Seasonal strength "
        f"{FMT_RHO.format(Fs)} ({_strength_band(Fs)}); trend strength "
        f"{FMT_RHO.format(Ft)} ({_strength_band(Ft)}). Use the trend "
        f"for growth-rate analysis and the seasonal for calendar-"
        f"pattern attribution; the residual captures what neither "
        f"component explained."
    )


def _tier2(results: dict) -> str:
    period = int(results.get("period", 0))
    seasonal_window = results.get("seasonal_window", "auto")
    robust = bool(results.get("robust", False))
    robust_clause = "robust fitting enabled" if robust else "non-robust fitting"
    return (
        f"Loess-based decomposition with seasonal window "
        f"s.window={seasonal_window} and {robust_clause}. Seasonal "
        f"strength computed as 1 − Var(R)/Var(S+R); trend strength as "
        f"1 − Var(R)/Var(T+R). STL's adaptive seasonality tolerates "
        f"gradual drift across the sample, unlike classical "
        f"decomposition's fixed seasonal pattern."
    )


def _trigger_near_noise(results: dict) -> Optional[str]:
    Fs = float(results.get("seasonal_strength", 0.0))
    Ft = float(results.get("trend_strength", 0.0))
    if Fs >= 0.3 or Ft >= 0.3:
        return None
    return (
        f"Both seasonal strength ({FMT_RHO.format(Fs)}) and trend "
        f"strength ({FMT_RHO.format(Ft)}) are below 0.30; the series "
        f"is near-noise and decomposition is uninformative. Consider "
        f"a simpler model or verify the series has the structure the "
        f"user expected."
    )


def _trigger_non_robust_large_residuals(results: dict) -> Optional[str]:
    if bool(results.get("robust", False)):
        return None
    if not bool(results.get("large_residuals_flagged")):
        return None
    return (
        "Non-robust STL flagged large residuals; enabling robust "
        "fitting (robust=True) down-weights outliers during the "
        "seasonal+trend extraction and often produces a cleaner "
        "decomposition on series with occasional shocks."
    )


SPEC = InterpretationSpec(
    technique_id="stl_decompose",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_near_noise, _trigger_non_robust_large_residuals),
    mode_aware=False,
)

register(SPEC)
