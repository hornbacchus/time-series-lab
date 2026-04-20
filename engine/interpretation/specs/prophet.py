"""
InterpretationSpec for prophet (Facebook Prophet).

Forecast-centric Tier 1 (per Phase 1 audit). Tier 2 discloses
Prophet's shrinkage-prior changepoint mechanism honestly — per
Decision 9, n_candidate_changepoints reflects the prior's candidate
list, not a count of statistically-significant breaks.
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


def _seasonality_active_clause(yearly_flag: str, weekly_flag: str) -> str:
    active = []
    yf = str(yearly_flag).lower()
    wf = str(weekly_flag).lower()
    if yf in {"true", "auto"}:
        active.append("yearly")
    if wf in {"true", "auto"}:
        active.append("weekly")
    if not active:
        return "No seasonal components active"
    if len(active) == 1:
        return f"{active[0].capitalize()} seasonality active"
    return f"{' and '.join(active).capitalize()} seasonality active"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
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
    seasonality_clause = _seasonality_active_clause(
        results.get("yearly_seasonality_flag", "auto"),
        results.get("weekly_seasonality_flag", "False"),
    )
    n_cp = int(results.get("n_candidate_changepoints", 0))
    recent_cp = results.get("most_recent_candidate_changepoint")
    if n_cp > 0:
        if recent_cp:
            cp_clause = (
                f"trend fit with {n_cp} candidate changepoints (most "
                f"recent at {recent_cp}), sparsity controlled by prior"
            )
        else:
            cp_clause = (
                f"trend fit with {n_cp} candidate changepoints, sparsity "
                f"controlled by prior"
            )
    else:
        cp_clause = "trend fit without changepoint flexibility"
    return (
        f"Prophet forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. "
        f"{seasonality_clause}; {cp_clause}."
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    cps = float(results.get("changepoint_prior_scale", 0.05))
    yearly = str(results.get("yearly_seasonality_flag", "auto")).lower()
    weekly = str(results.get("weekly_seasonality_flag", "False")).lower()
    yearly_desc = (
        "yearly seasonality (Fourier order 10)" if yearly in {"true", "auto"}
        else "yearly seasonality disabled"
    )
    weekly_desc = (
        "weekly seasonality enabled" if weekly in {"true", "auto"}
        else "weekly seasonality disabled"
    )
    n_cp = int(results.get("n_candidate_changepoints", 0))
    recent_cp = results.get("most_recent_candidate_changepoint")
    recent_clause = (
        f"; most recent candidate at {recent_cp}" if recent_cp else ""
    )
    rmse = results.get("fit_rmse")
    r2 = results.get("r2")
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "not reported"
    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "not reported"
    interval_pct = int(round(float(results.get("interval_width", 0.95)) * 100))
    backend = str(results.get("backend", "prophet"))
    backend_desc = (
        "Stan MAP via cmdstanpy (no MCMC sampling — posterior uncertainty "
        "may be underestimated on small samples)"
        if backend == "prophet"
        else f"seasonal-naive fallback (Prophet library unavailable; {backend})"
    )
    # Revision 7: appended actionable sentence on interpreting candidate
    # changepoints as a flexibility budget.
    return (
        f"Facebook Prophet additive model: piecewise-linear trend with "
        f"changepoint_prior_scale={FMT_COEF_UNSIGNED.format(cps)} + "
        f"{yearly_desc} + {weekly_desc} + no holiday component. "
        f"{n_cp} candidate changepoints placed uniformly in the first "
        f"80% of history under an L1-shrinkage prior (most candidates "
        f"receive near-zero weight){recent_clause}. {interval_pct}% "
        f"prediction intervals (forced at the wrapper to match TSL's "
        f"convention; Prophet's library default is 80%). Fit RMSE "
        f"{rmse_str}, R²={r2_str} on {n} observations. Backend: "
        f"{backend_desc}. Prophet's changepoint detection is data-driven "
        f"via L1 shrinkage, not a threshold-based selection; changepoint "
        f"count reflects the prior's candidate list, not a count of "
        f"statistically-significant trend breaks. Interpret the {n_cp} "
        f"candidates as a flexibility budget the trend can use if the "
        f"data supports it, not as {n_cp} identified regime shifts."
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
        f"Fit RMSE {format_scale_aware(float(fit))} matches or exceeds "
        f"the {label} baseline's {format_scale_aware(float(base))}. The "
        f"model does not beat naive on this series; reconsider "
        f"specification."
    )


def _trigger_high_changepoint_density(results: dict) -> Optional[str]:
    n_cp = results.get("n_candidate_changepoints")
    n_obs = results.get("n_obs")
    if n_cp is None or n_obs is None:
        return None
    n_cp = int(n_cp)
    n_obs = int(n_obs)
    if n_obs <= 0:
        return None
    if n_cp / n_obs <= 0.2:
        return None
    return (
        f"Detected {n_cp} candidate changepoints in {n_obs} observations "
        f"(>20% density); consider reducing n_changepoints or increasing "
        f"changepoint_prior_scale to enforce sparsity."
    )


def _trigger_logistic_growth_missing(results: dict) -> Optional[str]:
    end_level = results.get("forecast_end_value")
    hist_max = results.get("historical_max")
    if end_level is None or hist_max is None:
        return None
    if float(hist_max) <= 0 or abs(float(end_level)) <= 2 * abs(float(hist_max)):
        return None
    return (
        f"Forecast extrapolates to {format_scale_aware(float(end_level))}, "
        f"more than 2× historical max {format_scale_aware(float(hist_max))}; "
        f"if the series has a natural saturation (penetration, capacity), "
        f"configure growth='logistic' with a cap."
    )


SPEC = InterpretationSpec(
    technique_id="prophet",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_high_changepoint_density,
        _trigger_logistic_growth_missing,
    ),
    mode_aware=False,
)

register(SPEC)
