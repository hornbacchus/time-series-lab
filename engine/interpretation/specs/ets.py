"""
InterpretationSpec for ets (state-space exponential smoothing).

Shares wrapper `ets_hw.py` with the holt_winters spec but frames the
fit from a state-space perspective. Component code composed spec-side
as "ETS(trend,seasonal)" from available wrapper fields (per Phase 2
Decision 8 Option C: error-type not exposed by wrapper).
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)

PRESET_GATED_KEYS = ()


_TYPE_LTR = {"add": "A", "mul": "M", None: "N", "": "N"}


def _component_code(trend_type, seasonal_type) -> str:
    t = _TYPE_LTR.get(trend_type, "N")
    s = _TYPE_LTR.get(seasonal_type, "N")
    return f"ETS({t},{s})"


def _consistency_rationale(trend_type, seasonal_type, series_min) -> str:
    # Short rationale sentence tailored to the component choice.
    # "A and B" joiner avoids the awkward "with ... with" reading when
    # the calling sentence already starts with "... with {rationale}".
    pieces = []
    if trend_type == "add":
        pieces.append("additive trend")
    elif trend_type == "mul":
        pieces.append("multiplicative trend")
    else:
        pieces.append("no trend")
    if seasonal_type == "add":
        pieces.append("additive seasonal")
    elif seasonal_type == "mul":
        pieces.append("multiplicative seasonal")
    else:
        pieces.append("no seasonal")
    base = " and ".join([pieces[0], pieces[1]]) if len(pieces) == 2 else pieces[0]
    if seasonal_type == "mul" and series_min > 0:
        return (
            f"{base} — consistent with the series' strictly positive levels "
            f"and growing seasonal amplitude"
        )
    return base


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    trend = results.get("trend_type")
    seasonal = results.get("seasonal_type")
    code = _component_code(trend, seasonal)
    series_min = float(results.get("series_min", 0.0))
    rationale = _consistency_rationale(trend, seasonal, series_min)
    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "seasonal-naive"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value", 0.0)),
        forecast_end_value=float(results.get("forecast_end_value", 0.0)),
        series_std=float(results.get("series_std", 0.0)),
        horizon=horizon,
    )
    return (
        f"{code} forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. "
        f"State-space exponential smoothing with {rationale}."
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    trend = results.get("trend_type")
    seasonal = results.get("seasonal_type")
    seasonal_period = results.get("seasonal_period")
    damped = bool(results.get("damped_trend", False))
    aic = results.get("aic")
    rmse = results.get("fit_rmse")
    alpha = results.get("alpha")
    beta = results.get("beta")
    gamma = results.get("gamma")
    phi = results.get("phi")

    trend_word = {"add": "additive", "mul": "multiplicative", None: "no"}.get(trend, "no")
    seasonal_word = {"add": "additive", "mul": "multiplicative", None: "no"}.get(seasonal, "no")
    if seasonal:
        spec_clause = (
            f"with {trend_word} trend and {seasonal_word} seasonal "
            f"(period {int(seasonal_period) if seasonal_period else 'N/A'})"
        )
    else:
        spec_clause = f"with {trend_word} trend, no seasonal component"

    params = []
    if alpha is not None:
        params.append(f"level α={FMT_COEF_UNSIGNED.format(float(alpha))}")
    if beta is not None:
        params.append(f"trend β={FMT_COEF_UNSIGNED.format(float(beta))}")
    if gamma is not None:
        params.append(f"seasonal γ={FMT_COEF_UNSIGNED.format(float(gamma))}")
    if phi is not None:
        params.append(f"damping φ={FMT_COEF_UNSIGNED.format(float(phi))}")
    params_clause = (
        ("Smoothing parameters optimized by likelihood: " + ", ".join(params) + ".")
        if params else "Smoothing parameters not reported."
    )
    damp_clause = (
        f"Damped trend {'enabled' if damped else 'disabled'}."
    )
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "not reported"
    return (
        f"Exponential smoothing {spec_clause}. {params_clause} {damp_clause} "
        f"Fit AIC {aic_str}, RMSE {rmse_str} on {n} observations. "
        f"The state-space recursion is mathematically equivalent to "
        f"Holt-Winters' updating equations under matching component choices "
        f"— ETS framing emphasizes the likelihood-based optimization; "
        f"Holt-Winters framing emphasizes the explicit updating equations."
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
        f"does not beat naive on this series; reconsider specification."
    )


def _trigger_multiplicative_on_nonpositive(results: dict) -> Optional[str]:
    seasonal = results.get("seasonal_type")
    series_min = results.get("series_min")
    if seasonal != "mul" or series_min is None:
        return None
    if float(series_min) > 0:
        return None
    return (
        "Multiplicative seasonal component on data with non-positive values; "
        "the wrapper may have silently fallen back to additive. Verify the "
        "seasonal type in the Model Summary table."
    )


def _trigger_high_level_alpha(results: dict) -> Optional[str]:
    alpha = results.get("alpha")
    if alpha is None or float(alpha) <= 0.9:
        return None
    return (
        f"Level smoothing α={FMT_COEF_UNSIGNED.format(float(alpha))} near 1 "
        f"— the fitted model approaches a random-walk level; data may not "
        f"support exponential smoothing."
    )


def _trigger_trend_smoothing_degenerate(results: dict) -> Optional[str]:
    beta = results.get("beta")
    trend = results.get("trend_type")
    if beta is None or trend is None:
        return None
    if float(beta) >= 0.01:
        return None
    # Revision 4: actionable remediation appended.
    return (
        f"Trend smoothing β={FMT_COEF_UNSIGNED.format(float(beta))} is at "
        f"the optimizer floor; the trend component is effectively frozen "
        f"at its initial slope (no trend adaptation). The forecast's "
        f"trend extrapolation relies on the initialization, not on "
        f"learning from the series. Inspect the fitted trend component "
        f"in the data tables; if it reads flat where visual inspection "
        f"of the series suggests a slope, refit with stronger initial-"
        f"trend estimation (method='estimated' or explicit initial_trend)."
    )


SPEC = InterpretationSpec(
    technique_id="ets",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_multiplicative_on_nonpositive,
        _trigger_high_level_alpha,
        _trigger_trend_smoothing_degenerate,
    ),
    mode_aware=False,
)

register(SPEC)
