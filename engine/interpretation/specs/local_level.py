"""
InterpretationSpec for local_level.

State-space local level model: y_t = μ_t + ε_t with μ_t = μ_{t-1} + η_t.
Tier 1 cites series name, horizon, fit RMSE vs last-value-naive, horizon
trend clause, and the signal-to-noise ratio q = σ²_η / σ²_ε with its
adjective band (very low / low / moderate / high / very high).
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


def _q_band_sentence(q, band_label):
    """Map q-band label to a plain-language consequence sentence."""
    if band_label is None:
        return ""
    b = str(band_label).lower()
    if b == "very low":
        return (
            "— the level component is near-deterministic; the model "
            "captures a nearly-constant mean with most variance "
            "absorbed by observation noise"
        )
    if b == "low":
        return (
            "— the level component changes slowly relative to "
            "observation noise, so the model's forecast reverts "
            "slowly to the smoothed level"
        )
    if b == "moderate":
        return (
            "— level and observation components contribute comparably "
            "to total variance"
        )
    if b == "high":
        return (
            "— the level component changes rapidly, so the forecast "
            "tracks recent observations closely"
        )
    if b == "very high":
        return (
            "— the level is near random-walk; forecasts are dominated "
            "by the most recent observation"
        )
    return ""


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    q = results.get("q_ratio")
    band_label = results.get("q_band_label")
    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "last-value naive"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value", 0.0)),
        forecast_end_value=float(results.get("forecast_end_value", 0.0)),
        series_std=float(results.get("series_std", 0.0)),
        series_mean=results.get("series_mean"),
        horizon=horizon,
    )
    if q is not None and band_label:
        # Route q through format_scale_aware so sub-1e-3 values render
        # via scientific notation (e.g., "5.0e-04") rather than
        # rounding to three-decimal zero. FMT_COEF_UNSIGNED was
        # acceptable while the only observed q values were in [0.01, 10];
        # real_gdp's q=0.0005 would render as "0.001" under .3f, hiding
        # the true magnitude.
        q_clause = (
            f" Signal-to-noise ratio q = σ²_η / σ²_ε = "
            f"{format_scale_aware(float(q))} ({band_label}) "
            f"{_q_band_sentence(q, band_label)}."
        )
    else:
        q_clause = ""
    return (
        f"Local level model fitted to {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}.{q_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    s2_obs = results.get("sigma_obs")
    s2_lvl = results.get("sigma_level")
    aic = results.get("aic")
    bic = results.get("bic")
    ll = results.get("log_likelihood")
    final_level = results.get("smoothed_final_level")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"
    ll_str = format_scale_aware(float(ll)) if ll is not None else "not reported"
    s2_obs_str = format_scale_aware(float(s2_obs)) if s2_obs is not None else "not reported"
    s2_lvl_str = format_scale_aware(float(s2_lvl)) if s2_lvl is not None else "not reported"
    fl_str = format_scale_aware(float(final_level)) if final_level is not None else "(not reported)"
    return (
        f"State-space local level specification: y_t = μ_t + ε_t with "
        f"μ_t = μ_{{t-1}} + η_t. Two variance components: σ²_ε = "
        f"{s2_obs_str} (observation noise) and σ²_η = {s2_lvl_str} "
        f"(level disturbance). Fit by maximum likelihood via statsmodels "
        f"UnobservedComponents with diffuse initialization. AIC {aic_str}, "
        f"BIC {bic_str}, log-likelihood {ll_str} on {n} observations. "
        f"The forecast is the smoothed final level ({fl_str}) extended "
        f"flat — local_level has no drift component, so multi-step "
        f"forecasts are constant at the last smoothed level. Tier 1 "
        f"cites the smoothed state, not the filtered state, because "
        f"the wrapper uses the retrospective smoother."
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
        f"does not beat naive on this series; a constant-forecast baseline "
        f"is competitive with the state-space fit."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None or float(jb_p) >= 0.05:
        return None
    from interpretation.primitives import FMT_P_VALUE
    p_str = "p<0.0001" if float(jb_p) < 1e-4 else f"p={FMT_P_VALUE.format(float(jb_p))}"
    return (
        f"Residual normality test rejects at the 5% level "
        f"(JB {p_str}); prediction intervals assume Gaussian errors "
        f"and may be mis-calibrated for this series. Consider "
        f"bootstrapped intervals or a heavier-tailed specification."
    )


SPEC = InterpretationSpec(
    technique_id="local_level",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_residuals_non_normal,
    ),
    mode_aware=False,
)

register(SPEC)
