"""
InterpretationSpec for local_linear_trend.

State-space local linear trend: y_t = μ_t + ε_t, μ_t = μ_{t-1} + β_{t-1}
+ η_t, β_t = β_{t-1} + ζ_t. Three variance components. Tier 1 cites
fit RMSE vs naive, horizon trend clause, and the slope-adaptivity
adjective band (near-linear / moderately adaptive / highly adaptive).

In-spec adjective bands per Prompt C3 Decision 2 (first use; TODO
future-promotion if a second distinct spec needs the same logic).
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)

PRESET_GATED_KEYS = ()


# In-spec slope-adaptivity bands (σ²_ζ / σ²_η). Prompt C3 Decision 2.
# TODO: promote to a shared helper if a second distinct spec needs the
# same ratio-based banding logic.
SLOPE_ADAPTIVITY_NEAR_LINEAR_MAX = 0.05
SLOPE_ADAPTIVITY_MODERATE_MAX = 1.0


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    slope_adap = results.get("slope_adaptivity")
    band = results.get("slope_adaptivity_band")
    final_slope = results.get("smoothed_final_slope")
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
    slope_clause = ""
    if slope_adap is not None and band and final_slope is not None:
        if band == "near-linear":
            descriptor = (
                "the trend is effectively a fixed linear drift; the "
                f"smoothed final slope {format_scale_aware(float(final_slope))} "
                f"projects forward deterministically"
            )
        elif band == "moderately adaptive":
            descriptor = (
                "the slope drifts moderately over time; the smoothed "
                f"final slope {format_scale_aware(float(final_slope))} "
                f"projects forward with modest uncertainty"
            )
        else:
            descriptor = (
                "the slope is highly adaptive; the smoothed final slope "
                f"{format_scale_aware(float(final_slope))} carries "
                f"substantial uncertainty into the forecast"
            )
        slope_clause = (
            f" Slope adaptivity σ²_ζ/σ²_η = "
            f"{format_scale_aware(float(slope_adap))} ({band}) — "
            f"{descriptor}."
        )
    return (
        f"Local linear trend model fitted to {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}.{slope_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    s2_obs = results.get("sigma_obs")
    s2_lvl = results.get("sigma_level")
    s2_trend = results.get("sigma_trend")
    aic = results.get("aic")
    rmse = results.get("fit_rmse")
    final_level = results.get("smoothed_final_level")
    final_slope = results.get("smoothed_final_slope")
    damped_not_wired = bool(results.get("damped_not_wired", False))

    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "not reported"
    s2_obs_str = format_scale_aware(float(s2_obs)) if s2_obs is not None else "not reported"
    s2_lvl_str = format_scale_aware(float(s2_lvl)) if s2_lvl is not None else "not reported"
    s2_trend_str = format_scale_aware(float(s2_trend)) if s2_trend is not None else "not reported"
    fl_str = format_scale_aware(float(final_level)) if final_level is not None else "not reported"
    fs_str = format_scale_aware(float(final_slope)) if final_slope is not None else "not reported"

    damping_clause = (
        " The ``damped`` parameter is accepted by the wrapper but is "
        "not currently wired into the fit; damping has no effect on "
        "this run."
        if damped_not_wired else ""
    )
    return (
        f"State-space local linear trend: y_t = μ_t + ε_t with μ_t = "
        f"μ_{{t-1}} + β_{{t-1}} + η_t and β_t = β_{{t-1}} + ζ_t. "
        f"Three variance components: σ²_ε = {s2_obs_str} (observation "
        f"noise), σ²_η = {s2_lvl_str} (level disturbance), σ²_ζ = "
        f"{s2_trend_str} (slope disturbance). Fit by maximum likelihood "
        f"via statsmodels UnobservedComponents. AIC {aic_str}, RMSE "
        f"{rmse_str} on {n} observations. Smoothed final level "
        f"{fl_str}, smoothed final slope {fs_str}. Long-horizon "
        f"forecast variance amplifies cubically with h under the "
        f"model's integrated-slope structure, so prediction bands "
        f"widen rapidly beyond 2-3 seasons.{damping_clause}"
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
        f"{label} baseline's {format_scale_aware(float(base))}. The "
        f"state-space model does not beat naive on this series; "
        f"reconsider the specification or use the simpler baseline."
    )


def _trigger_slope_variance_collapsed(results: dict) -> Optional[str]:
    """D6 (post-Phase 1 refinement): slope variance at the optimizer
    floor — named component, named consequence, actionable remediation."""
    s2_trend = results.get("sigma_trend")
    s2_lvl = results.get("sigma_level")
    if s2_trend is None or s2_lvl is None:
        return None
    try:
        max_variance = max(
            float(v) for v in (
                results.get("sigma_obs"),
                results.get("sigma_level"),
                results.get("sigma_trend"),
            )
            if v is not None
        )
    except ValueError:
        return None
    if max_variance <= 0:
        return None
    if float(s2_trend) > 1e-8 * max_variance:
        return None
    return (
        f"The slope variance σ²_ζ = {format_scale_aware(float(s2_trend))} "
        f"is at the optimizer floor — the trend component is effectively "
        f"a fixed (non-stochastic) slope. The fitted model behaves as a "
        f"local-level model with linear drift; if a stochastic slope is "
        f"needed, the series may not have enough variation to identify one."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None or float(jb_p) >= 0.05:
        return None
    p_str = "p<0.0001" if float(jb_p) < 1e-4 else f"p={FMT_P_VALUE.format(float(jb_p))}"
    return (
        f"Residual normality test rejects at the 5% level "
        f"(JB {p_str}); prediction intervals assume Gaussian errors "
        f"and may be mis-calibrated. Consider bootstrapped intervals "
        f"or a heavier-tailed specification."
    )


def _trigger_residual_autocorrelation(results: dict) -> Optional[str]:
    lb_p = results.get("ljung_box_lag10_pvalue")
    if lb_p is None or float(lb_p) >= 0.05:
        return None
    p_str = "p<0.0001" if float(lb_p) < 1e-4 else f"p={FMT_P_VALUE.format(float(lb_p))}"
    return (
        f"Residual Ljung-Box at lag 10 rejects white-noise "
        f"({p_str}); the model leaves structure in the residuals. "
        f"Consider seasonal terms (via structural_ts) or a "
        f"multiplicative transformation."
    )


SPEC = InterpretationSpec(
    technique_id="local_linear_trend",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_slope_variance_collapsed,
        _trigger_residuals_non_normal,
        _trigger_residual_autocorrelation,
    ),
    mode_aware=False,
)

register(SPEC)
