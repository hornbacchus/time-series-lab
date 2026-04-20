"""
InterpretationSpec for holt_winters (trend + seasonal, explicit).

Shares wrapper `ets_hw.py` with the ets spec but frames the fit from
the explicit updating-equations perspective (Holt 1957, Winters 1960).
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


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    trend = results.get("trend_type")
    seasonal = results.get("seasonal_type")
    period = results.get("seasonal_period")
    damped = bool(results.get("damped_trend", False))
    trend_word = {"add": "Additive", "mul": "Multiplicative", None: "No"}.get(trend, "No")
    seasonal_word = {"add": "additive", "mul": "multiplicative", None: "no"}.get(seasonal, "no")
    if seasonal and period:
        spec_sentence = (
            f"{trend_word} trend with {seasonal_word} seasonal "
            f"(period {int(period)}); damping {'enabled' if damped else 'disabled'}."
        )
    else:
        spec_sentence = (
            f"{trend_word} trend, no seasonal; damping "
            f"{'enabled' if damped else 'disabled'}."
        )
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
        f"Holt-Winters forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. {spec_sentence}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    trend = results.get("trend_type")
    seasonal = results.get("seasonal_type")
    period = results.get("seasonal_period")
    damped = bool(results.get("damped_trend", False))
    alpha = results.get("alpha")
    beta = results.get("beta")
    gamma = results.get("gamma")
    phi = results.get("phi")
    aic = results.get("aic")
    rmse = results.get("fit_rmse")

    trend_word = {"add": "additive", "mul": "multiplicative"}.get(trend, trend or "no")
    seasonal_word = {"add": "additive", "mul": "multiplicative"}.get(seasonal, seasonal or "no")
    m = int(period) if period else 0
    # Updating equations, rendered via multiplicative-seasonal form as
    # a concrete example (the canonical airline case). Falls back to
    # simpler wording if seasonal is None.
    if seasonal == "mul" and m > 0:
        eqns = (
            f"Updating equations: ℓ_t = α(y_t / s_{{t-{m}}}) + "
            f"(1-α)(ℓ_{{t-1}} + b_{{t-1}}); b_t = β(ℓ_t - ℓ_{{t-1}}) + "
            f"(1-β)b_{{t-1}}; s_t = γ(y_t / ℓ_t) + (1-γ)s_{{t-{m}}}."
        )
    elif seasonal == "add" and m > 0:
        eqns = (
            f"Updating equations: ℓ_t = α(y_t - s_{{t-{m}}}) + "
            f"(1-α)(ℓ_{{t-1}} + b_{{t-1}}); b_t = β(ℓ_t - ℓ_{{t-1}}) + "
            f"(1-β)b_{{t-1}}; s_t = γ(y_t - ℓ_t) + (1-γ)s_{{t-{m}}}."
        )
    else:
        eqns = (
            "Updating equations: ℓ_t = αy_t + (1-α)(ℓ_{t-1} + b_{t-1}); "
            "b_t = β(ℓ_t - ℓ_{t-1}) + (1-β)b_{t-1}."
        )

    params = []
    if alpha is not None:
        params.append(f"α={FMT_COEF_UNSIGNED.format(float(alpha))}")
    if beta is not None:
        params.append(f"β={FMT_COEF_UNSIGNED.format(float(beta))}")
    if gamma is not None:
        params.append(f"γ={FMT_COEF_UNSIGNED.format(float(gamma))}")
    if phi is not None and damped:
        params.append(f"φ={FMT_COEF_UNSIGNED.format(float(phi))}")
    params_clause = (f"Smoothing: {', '.join(params)}." if params else "")

    horizon_val = int(results.get("horizon", 0))
    damping_advice = (
        " Undamped trend extrapolates linearly at horizon — long-horizon "
        "forecasts carry trend-amplification risk; enable damping (φ < 1) "
        "if the horizon exceeds one to two full seasons."
        if (not damped and m > 0) else ""
    )
    seasonal_clause = (
        f"Holt-Winters with {trend_word} linear trend and {seasonal_word} "
        f"seasonality at period {m} "
        + ("(monthly)" if m == 12 else f"({_period_name(m)})" if m > 0 else "")
        + ". "
    ) if m > 0 else (
        f"Holt-Winters with {trend_word} linear trend (no seasonal). "
    )
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "not reported"
    return (
        f"{seasonal_clause}{eqns} {params_clause} Initial seasonal indices "
        f"estimated from the first full seasonal cycle. Fit AIC {aic_str}, "
        f"RMSE {rmse_str} on {n} observations.{damping_advice}"
    )


def _period_name(m):
    return {4: "quarterly", 7: "daily", 12: "monthly", 52: "weekly"}.get(int(m), f"period {m}")


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
        "Multiplicative seasonal on data with non-positive values; the "
        "wrapper may have silently fallen back to additive. Verify the "
        "seasonal type in the Model Summary table."
    )


def _trigger_long_horizon_no_damping(results: dict) -> Optional[str]:
    damped = bool(results.get("damped_trend", False))
    horizon = int(results.get("horizon", 0))
    period = results.get("seasonal_period")
    if damped or not period or horizon <= 2 * int(period):
        return None
    return (
        f"Undamped trend projected over {horizon} periods (>2× seasonal "
        f"period {int(period)}); enable damping to prevent trend "
        f"extrapolation divergence."
    )


def _trigger_trend_smoothing_degenerate(results: dict) -> Optional[str]:
    beta = results.get("beta")
    if beta is None:
        return None
    if float(beta) >= 0.01:
        return None
    return (
        f"Trend smoothing β={FMT_COEF_UNSIGNED.format(float(beta))} is at "
        f"the optimizer floor — the trend is effectively frozen at its "
        f"initial slope. The forecast's trend extrapolation relies on the "
        f"initialization, not on learning from the data. Inspect the "
        f"fitted trend component in the data tables; if it reads flat "
        f"where visual inspection of the series suggests a slope, refit "
        f"with stronger initial-trend estimation (method='estimated' or "
        f"explicit initial_trend)."
    )


SPEC = InterpretationSpec(
    technique_id="holt_winters",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_multiplicative_on_nonpositive,
        _trigger_long_horizon_no_damping,
        _trigger_trend_smoothing_degenerate,
    ),
    mode_aware=False,
)

register(SPEC)
