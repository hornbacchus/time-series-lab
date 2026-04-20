"""
InterpretationSpec for classical_decompose.

Tier 1 leads with seasonal/trend strength and period. Tier 2 discloses
the classical ratio-to-moving-average method and caveats stable
seasonality assumption.
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
    dominant = "trend" if Ft >= Fs else "seasonal"
    return (
        f"Classical decomposition of {format_series_reference(name)} "
        f"({n} observations, period {period}). Seasonal strength "
        f"{FMT_RHO.format(Fs)} ({_strength_band(Fs)}); trend strength "
        f"{FMT_RHO.format(Ft)} ({_strength_band(Ft)}). The {dominant} "
        f"component carries most of the variation — seasonally-adjusted "
        f"values in the data tables isolate the trend-cycle for "
        f"downstream analysis."
    )


def _tier2(results: dict) -> str:
    period = int(results.get("period", 0))
    model_type = str(results.get("model_type", "additive"))
    two_sided = bool(results.get("two_sided", True))
    ma_desc = "two-sided centered moving average" if two_sided else "one-sided trailing moving average"
    return (
        f"{model_type.capitalize()} decomposition with {ma_desc} at "
        f"period {period}. Seasonal and trend components extracted via "
        f"the classical ratio-to-moving-average method. Residual "
        f"diagnostics appear in the data tables. Method assumes stable "
        f"seasonality across the sample — consider MSTL or X-13 if "
        f"seasonality evolves."
    )


def _trigger_residual_structure(results: dict) -> Optional[str]:
    lb_p = results.get("residual_ljung_box_p")
    if lb_p is None:
        return None
    if float(lb_p) >= 0.05:
        return None
    return (
        f"Residual Ljung-Box rejects white-noise at the 5% level "
        f"(p={float(lb_p):.4f}); residuals carry structure that the "
        f"decomposition did not capture. Consider an alternative "
        f"method (STL, MSTL, or X-13) or examine residual ACF."
    )


def _trigger_multiplicative_non_positive(results: dict) -> Optional[str]:
    if not bool(results.get("multiplicative_on_nonpositive")):
        return None
    return (
        "Multiplicative decomposition was requested on a series with "
        "non-positive values; the wrapper auto-switched to additive to "
        "avoid log-undefined terms. Re-examine whether additive is the "
        "appropriate model."
    )


SPEC = InterpretationSpec(
    technique_id="classical_decompose",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_residual_structure, _trigger_multiplicative_non_positive),
    mode_aware=False,
)

register(SPEC)
