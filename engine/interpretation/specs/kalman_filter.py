"""
InterpretationSpec for kalman_filter (Follow-up 2a).

Direct-access Kalman filter with four named templates (local_level,
local_linear_trend, seasonal, ar1) plus a custom path accepting
user-supplied (Z, T, R, H, Q) matrices. Produces online one-step-
ahead state estimates conditioned on y_{1:t}.

Tier 1: state-space skeleton + final filtered state + baseline
comparison + horizon trend clause + RMSE.

Tier 2: filter vs smoother disclosure + model equations (template)
or custom matrix disclosure (custom path) + initialization +
likelihood summary + variance components + residual diagnostics.

Tier 3 triggers (shared from _state_space_common + filter-specific):
- JB non-normality
- LB residual autocorrelation
- RMSE exceeds baseline
- Convergence warning (template path only)
- Custom-path no-MLE disclosure (always on custom path)
- Filter-specific: low-q ratio (local_level only)
- Filter-specific: early-period initialization sensitivity
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
    skeleton = render_state_space_tier1_skeleton(results, "filter")
    final_state = render_final_state_summary(results, "filter")
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
    parts.append(
        f"{horizon}-step forecast: {trend_clause}. {baseline_clause}."
    )
    return " ".join(parts)


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------


def _tier2(results: dict) -> str:
    template = str(results.get("state_space_model", ""))

    parts = [render_filter_vs_smoother_disclosure("filter")]

    # Model structure: equations (template) or custom-matrix disclosure
    if template == "custom":
        parts.append(render_custom_matrix_disclosure(results))
    else:
        eq = render_model_equations(template, results)
        if eq:
            parts.append(eq)

    # Initialization
    parts.append(render_initialization_disclosure(results))

    # Variance components (template only)
    if template != "custom":
        vc = render_variance_components(results)
        if vc:
            parts.append(vc)

    # Likelihood / AIC / BIC
    ll = render_likelihood_summary(results)
    if ll:
        parts.append(ll)

    # Residual diagnostics
    rd = render_residual_diagnostics(results)
    if rd:
        parts.append(rd)

    # Forecast mechanism
    parts.append(
        "Forecasts extend the filtered state trajectory forward using "
        "the model's transition dynamics."
    )

    return " ".join(parts)


# ---------------------------------------------------------------------
# Filter-specific Tier 3 triggers
# ---------------------------------------------------------------------


def _trigger_low_signal_to_noise(results: dict) -> Optional[str]:
    """Fires when q-ratio < 0.05 on local_level / local_linear_trend.

    A very-low q means the level is near-deterministic; the filter
    follows a near-constant trajectory and the state estimates are
    heavily smoothed toward their prior. Users should consider a
    richer model (add a slope or seasonal component) or a different
    family (volatility model if the series is returns-like).
    """
    template = str(results.get("state_space_model", ""))
    if template not in ("local_level", "local_linear_trend"):
        return None
    q = results.get("q_ratio")
    if q is None or float(q) >= 0.05:
        return None
    return (
        f"Low signal-to-noise ratio (q = {format_scale_aware(float(q))}). "
        f"The level estimate is heavily smoothed toward its prior "
        f"trajectory — the model treats the series as near-constant "
        f"plus noise. Consider adding a slope component "
        f"(local_linear_trend) or switching to a volatility model if "
        f"the series is returns-like."
    )


def _trigger_early_period_init_sensitivity(results: dict) -> Optional[str]:
    """Fires on diffuse init + short series + small state dim.

    Early-period filtered states depend heavily on the initialization
    until the Kalman gain has propagated several observations. This
    is a specific concern for the filter (the smoother revises these
    early estimates).
    """
    init = str(results.get("initialization", ""))
    n = int(results.get("n_obs", 0))
    state_dim = int(results.get("state_dim", 0))
    if init != "diffuse":
        return None
    if n >= 50 or state_dim > 3:
        return None
    return (
        f"Early-period initialization sensitivity: with diffuse init "
        f"and only {n} observations, the first ~5–10 filtered states "
        f"may be dominated by the initial-covariance prior rather than "
        f"the data. The filter's uncertainty is widest at t=1 and "
        f"contracts as more observations accumulate. For retrospective "
        f"analysis on this short series, use kalman_smoother (which "
        f"revises early states using the full sample)."
    )


# ---------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------


SPEC = InterpretationSpec(
    technique_id="kalman_filter",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_convergence_warning,
        _trigger_jb_nonnormal,
        _trigger_lb_residual_ac,
        _trigger_rmse_exceeds_baseline,
        _trigger_custom_path_no_mle,
        _trigger_low_signal_to_noise,
        _trigger_early_period_init_sensitivity,
    ),
    mode_aware=False,
)


register(SPEC)
