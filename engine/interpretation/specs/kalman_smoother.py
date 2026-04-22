"""
InterpretationSpec for kalman_smoother (Follow-up 2a).

Direct-access Kalman smoother with four named templates (local_level,
local_linear_trend, seasonal, ar1) plus a custom path accepting
user-supplied (Z, T, R, H, Q) matrices. Produces retrospective
smoothed state estimates conditioned on y_{1:T}.

On Balanced/Thorough presets (or when compute_ci=True), also emits
smoothed disturbance estimates (ε̂_t, η̂_t | y_{1:T}) for shock
attribution.

Tier 1: state-space skeleton + final smoothed state + optional
disturbance-smoother closing clause + baseline comparison + horizon
trend clause.

Tier 2: filter vs smoother disclosure (smoother-side framing) +
model equations or custom matrix disclosure + initialization +
likelihood summary + variance components + residual diagnostics +
disturbance-smoother disclosure (when computed).

Tier 3 triggers (shared + smoother-specific):
- JB non-normality
- LB residual autocorrelation
- RMSE exceeds baseline
- Convergence warning (template path only)
- Custom-path no-MLE disclosure
- Smoother-specific: smoother_far_from_filter (retrospective
  revisions materially changed the filtered state).
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import format_scale_aware
from interpretation.registry import register
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)
from interpretation.specs._state_space_common import (
    render_state_space_tier1_skeleton,
    render_final_state_summary,
    render_filter_vs_smoother_disclosure,
    render_initialization_disclosure,
    render_model_equations,
    render_custom_matrix_disclosure,
    render_likelihood_summary,
    render_variance_components,
    render_residual_diagnostics,
    _trigger_jb_nonnormal,
    _trigger_lb_residual_ac,
    _trigger_rmse_exceeds_baseline,
    _trigger_convergence_warning,
    _trigger_custom_path_no_mle,
)


PRESET_GATED_KEYS = ()


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------


def _tier1(results: dict) -> str:
    skeleton = render_state_space_tier1_skeleton(results, "smoother")
    final_state = render_final_state_summary(results, "smoother")
    horizon = int(results.get("horizon", 0))
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
    parts = [skeleton]
    if final_state:
        parts.append(final_state)

    # Disturbance-smoother closing clause
    if results.get("disturbance_smoother_computed"):
        parts.append(
            "Disturbance smoother computed; see the Smoothed Disturbance "
            "data table."
        )

    parts.append(
        f"{horizon}-step forecast: {trend_clause}. {baseline_clause}."
    )
    return " ".join(parts)


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------


def _tier2(results: dict) -> str:
    template = str(results.get("state_space_model", ""))

    parts = [render_filter_vs_smoother_disclosure("smoother")]

    if template == "custom":
        parts.append(render_custom_matrix_disclosure(results))
    else:
        eq = render_model_equations(template, results)
        if eq:
            parts.append(eq)

    parts.append(render_initialization_disclosure(results))

    if template != "custom":
        vc = render_variance_components(results)
        if vc:
            parts.append(vc)

    ll = render_likelihood_summary(results)
    if ll:
        parts.append(ll)

    rd = render_residual_diagnostics(results)
    if rd:
        parts.append(rd)

    # Disturbance-smoother specific disclosure
    if results.get("disturbance_smoother_computed"):
        parts.append(
            "The disturbance smoother estimates the realized observation "
            "and state shocks (ε̂_t, η̂_t | y_{1:T}) using the full "
            "sample; these are useful for residual-based diagnostics "
            "and attributing historical movements to specific shocks. "
            "See the Smoothed Disturbance data table."
        )

    # Forecast mechanism: smoothing doesn't change out-of-sample paths
    parts.append(
        "Forecasts extend the smoothed final-state trajectory forward "
        "using the model's transition dynamics; since the smoothed and "
        "filtered states coincide at t=T (both condition on y_{1:T} "
        "at the final period), forecasts are identical to what the "
        "filter would produce."
    )

    return " ".join(parts)


# ---------------------------------------------------------------------
# Smoother-specific Tier 3 triggers
# ---------------------------------------------------------------------


def _trigger_smoother_far_from_filter(results: dict) -> Optional[str]:
    """Fires when mean |smoothed - filtered| > 2x mean filter SE.

    Indicates the retrospective smoother materially revised the
    filtered estimates — usually because the series exhibits
    short-run noise that the filter initially attributed to the
    level but the smoother recognized as transient.
    """
    diff = results.get("mean_abs_smoothed_minus_filtered")
    filter_se = results.get("mean_filter_se")
    if diff is None or filter_se is None or float(filter_se) <= 0:
        return None
    ratio = float(diff) / float(filter_se)
    if ratio <= 2.0:
        return None
    return (
        f"The smoother materially revised the filtered estimates: "
        f"mean absolute smoothed-vs-filtered difference is "
        f"{format_scale_aware(float(diff))}, which is {ratio:.1f}× the "
        f"mean filter SE ({format_scale_aware(float(filter_se))}). This "
        f"indicates that later observations substantially changed the "
        f"retrospective view of early-period states — use the smoother "
        f"for historical analysis, not the filter."
    )


# ---------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------


SPEC = InterpretationSpec(
    technique_id="kalman_smoother",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_convergence_warning,
        _trigger_jb_nonnormal,
        _trigger_lb_residual_ac,
        _trigger_rmse_exceeds_baseline,
        _trigger_custom_path_no_mle,
        _trigger_smoother_far_from_filter,
    ),
    mode_aware=False,
)


register(SPEC)
