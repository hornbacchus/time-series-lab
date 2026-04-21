"""
InterpretationSpec for structural_ts (Unobserved Components Model).

Flexible UCM carrying any combination of level / trend / seasonal /
cycle / AR components. Tier 1 uses a single parameterized template
(per Prompt C3 Decision 1) that dynamically cites the active
components list and names the dominant component by variance share.
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


def _components_phrase(components, seasonal_period):
    """Render the active-components list as a prose phrase.

    e.g., ['Level', 'Trend', 'Seasonal', 'Cycle'] →
    "level, trend, seasonal (period 12), and cycle".
    """
    if not components:
        return "no active components"
    parts = []
    for c in components:
        low = str(c).lower()
        if low == "seasonal" and seasonal_period:
            parts.append(f"{low} (period {int(seasonal_period)})")
        else:
            parts.append(low)
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    components = list(results.get("components") or [])
    seasonal_period = results.get("seasonal_period")
    vd = results.get("variance_decomposition") or {}
    dominant = results.get("dominant_component")
    comp_phrase = _components_phrase(components, seasonal_period)
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
    dominance_clause = ""
    if dominant and dominant in vd:
        dom_pct = float(vd[dominant].get("pct_of_total", 0.0))
        other_pct = max(0.0, 100.0 - dom_pct)
        dominance_clause = (
            f" {dominant} dominates the variance decomposition "
            f"({dom_pct:.1f}%); the remaining components together account "
            f"for the remaining {other_pct:.1f}% of total variance."
        )
    return (
        f"Structural TS with {comp_phrase} components fitted to "
        f"{format_series_reference(name)} ({n} observations) over "
        f"{horizon} periods. {baseline_clause}; {trend_clause}."
        f"{dominance_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    components = list(results.get("components") or [])
    vd = results.get("variance_decomposition") or {}
    level_type = str(results.get("level_type", "local level"))
    seasonal_period = results.get("seasonal_period")
    cycle_enabled = bool(results.get("cycle_enabled", False))
    ar_order = int(results.get("ar_order", 0))
    aic = results.get("aic")
    bic = results.get("bic")
    ll = results.get("log_likelihood")
    dw = results.get("durbin_watson")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"
    ll_str = format_scale_aware(float(ll)) if ll is not None else "not reported"

    # Component list sentence fragments
    comp_parts = [f"level ({level_type} specification)"]
    if "Trend" in components:
        comp_parts.append("trend (slope disturbance)")
    if "Seasonal" in components and seasonal_period:
        comp_parts.append(f"seasonal (period {int(seasonal_period)})")
    if cycle_enabled:
        comp_parts.append("cycle (bounded frequency 2-12)")
    if ar_order > 0:
        comp_parts.append(f"AR({ar_order})")
    comp_sentence = ", ".join(comp_parts)

    # Variance-share sentence
    share_parts = []
    for cname in list(vd.keys()):
        pct = float(vd[cname].get("pct_of_total", 0.0))
        share_parts.append(f"{cname} {pct:.1f}%")
    share_sentence = (
        f"Per-component variance shares: {', '.join(share_parts)}."
        if share_parts else ""
    )

    # Durbin-Watson diagnostic
    dw_clause = ""
    if dw is not None:
        dw_f = float(dw)
        ac_sense = "substantial positive" if dw_f < 1.5 else (
            "substantial negative" if dw_f > 2.5 else "minimal"
        )
        if ac_sense != "minimal":
            dw_clause = (
                f" Residual Durbin-Watson {dw_f:.2f} indicates "
                f"{ac_sense} autocorrelation — the model captures the "
                f"macro-level structure but leaves short-horizon "
                f"correlation in the residuals."
            )

    # UCM canonical reduction note — when trend variance is
    # effectively zero and level dominates, the fit collapses to a
    # simpler specification.
    vd_trend = vd.get("Trend", {})
    vd_level = vd.get("Level", {})
    reduction_clause = ""
    if (
        vd_trend.get("pct_of_total", 1.0) < 0.5
        and vd_level.get("pct_of_total", 0.0) > 80.0
    ):
        reduction_clause = (
            " With trend variance collapsed and level dominant, this "
            "UCM is effectively a local_level with seasonal-plus-cycle "
            "refinement; refitting with level='local level' would yield "
            "comparable AIC with fewer parameters."
        )

    return (
        f"Unobserved Components Model (UCM) with {len(components)} active "
        f"components: {comp_sentence}. Fit by maximum likelihood via "
        f"statsmodels UnobservedComponents with diffuse initialization. "
        f"{share_sentence} AIC {aic_str}, BIC {bic_str}, "
        f"log-likelihood {ll_str} on {n} observations.{dw_clause}"
        f"{reduction_clause}"
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
        f"UCM does not beat naive on this series; reconsider which "
        f"components are enabled or use the simpler baseline."
    )


def _trigger_component_variance_collapsed(results: dict) -> Optional[str]:
    """D6 refined trigger: fires when any component's variance is
    effectively zero relative to the maximum variance across
    components (< 1e-8 × max_variance per D9). Names the specific
    component and the consequence."""
    vd = results.get("variance_decomposition") or {}
    if not vd:
        return None
    variances = [
        float(v.get("variance", 0.0))
        for k, v in vd.items()
        if k != "Residual"
    ]
    variances = [v for v in variances if v >= 0]
    if not variances:
        return None
    max_var = max(variances)
    if max_var <= 0:
        return None
    collapsed = []
    for cname, details in vd.items():
        if cname == "Residual":
            continue
        v = float(details.get("variance", 0.0))
        if v < 1e-8 * max_var:
            collapsed.append((cname, v))
    if not collapsed:
        return None
    # Fire on the first collapsed component (typically the most
    # informative; multi-collapse cases are rare).
    cname, v = collapsed[0]
    return (
        f"The {cname} component's variance σ²_{cname} = "
        f"{format_scale_aware(v)} is at the optimizer floor relative "
        f"to the other components, indicating the model collapsed this "
        f"component to effectively deterministic. The fitted model "
        f"behaves as if {cname} were removed; consider refitting with "
        f"only the active components to get cleaner parameter estimates."
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
        f"({p_str}); the UCM leaves short-horizon structure in the "
        f"residuals. Consider enabling additional components (AR term, "
        f"cycle) or extending the seasonal specification."
    )


SPEC = InterpretationSpec(
    technique_id="structural_ts",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_component_variance_collapsed,
        _trigger_residuals_non_normal,
        _trigger_residual_autocorrelation,
    ),
    mode_aware=False,
)

register(SPEC)
