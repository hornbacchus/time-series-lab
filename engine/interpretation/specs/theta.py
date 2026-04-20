"""
InterpretationSpec for theta (Theta method, Assimakopoulos & Nikolopoulos 2000).

Classical decomposition-based forecaster. Tier 2 describes the two
theta-lines (θ=0 drift, θ=2 SES) qualitatively — statsmodels'
ThetaModel does not expose individual theta-line coefficients, so
Phase 2 Decision 6 locks in qualitative-only component disclosure.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    deseasonalized = bool(results.get("deseasonalized", False))
    period = results.get("seasonal_period")
    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "seasonal-naive"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value", 0.0)),
        forecast_end_value=float(results.get("forecast_end_value", 0.0)),
        series_std=float(results.get("series_std", 0.0)),
        series_mean=results.get("series_mean"),
        horizon=horizon,
    )
    if deseasonalized and period:
        seasonal_clause = (
            f"Seasonal pre-adjustment applied (multiplicative, period "
            f"{int(period)}); the seasonal pattern is re-applied to the "
            f"forecast."
        )
    elif deseasonalized:
        seasonal_clause = (
            "Seasonal pre-adjustment applied; the seasonal pattern is "
            "re-applied to the forecast."
        )
    else:
        seasonal_clause = "No seasonal pre-adjustment applied."
    return (
        f"Theta forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. {seasonal_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    deseasonalized = bool(results.get("deseasonalized", False))
    period = results.get("seasonal_period")
    rmse = results.get("fit_rmse")
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "not reported"
    if deseasonalized and period:
        seasonal_sentence = (
            f"Seasonal pre-adjustment is applied before decomposition "
            f"(multiplicative, period {int(period)}); the seasonal pattern "
            f"is re-applied to the forecast."
        )
    elif deseasonalized:
        seasonal_sentence = (
            "Seasonal pre-adjustment is applied before decomposition; the "
            "seasonal pattern is re-applied to the forecast."
        )
    else:
        seasonal_sentence = "Seasonal pre-adjustment disabled."
    # Revision 5: "qualitative rather than numeric" (drops "citation-form"
    # internal vocabulary).
    return (
        f"Theta method (Assimakopoulos & Nikolopoulos 2000): the series "
        f"is decomposed into two theta-lines — θ=0 (linear drift trend) "
        f"and θ=2 (short-term nonlinear component via simple exponential "
        f"smoothing) — forecast independently and recombined as a simple "
        f"average. {seasonal_sentence} Fit RMSE {rmse_str} on {n} "
        f"observations. Theta is a strong M3-competition benchmark for "
        f"short-horizon forecasts on seasonal series; longer horizons, "
        f"non-seasonal series, or non-stationary regimes can degrade "
        f"Theta's accuracy relative to exponential-smoothing or ARIMA "
        f"alternatives. Statsmodels' ThetaModel does not expose the "
        f"individual theta-line coefficients numerically, so the "
        f"component description above is qualitative rather than numeric."
    )


def _trigger_rmse_exceeds_naive(results: dict) -> Optional[str]:
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None or float(base) <= 0:
        return None
    if float(fit) < float(base):
        return None
    label = results.get("baseline_label", "naive")
    return (
        f"Fit RMSE {format_scale_aware(float(fit))} matches or exceeds the "
        f"{label} baseline's {format_scale_aware(float(base))}. The model "
        f"does not beat naive on this series; prefer the simpler naive "
        f"forecast or try a different method."
    )


def _trigger_long_horizon_caution(results: dict) -> Optional[str]:
    horizon = int(results.get("horizon", 0))
    period = results.get("seasonal_period")
    if not period or horizon <= 2 * int(period):
        return None
    return (
        f"Forecast horizon {horizon} exceeds 2× seasonal period {int(period)} "
        f"— Theta's benchmark strength concentrates in short-horizon "
        f"M3-style cases; treat longer-horizon forecasts cautiously."
    )


def _trigger_non_seasonal_series(results: dict) -> Optional[str]:
    # Fires when deseasonalize is disabled on a presumptively seasonal
    # series. The wrapper currently does not flag seasonality detection,
    # so this trigger is conservative — fires only when seasonal_period
    # is supplied (user-specified) but deseasonalized=False.
    deseasonalized = bool(results.get("deseasonalized", False))
    period = results.get("seasonal_period")
    if deseasonalized:
        return None
    if not period:
        return None
    return (
        f"Seasonal pre-adjustment is disabled (deseasonalize=False) but a "
        f"seasonal period {int(period)} is specified; consider enabling "
        f"deseasonalize=True for series with seasonal structure."
    )


SPEC = InterpretationSpec(
    technique_id="theta",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_long_horizon_caution,
        _trigger_non_seasonal_series,
    ),
    mode_aware=False,
)

register(SPEC)
