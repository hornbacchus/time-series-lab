"""
Shared helpers for Follow-up 2a kalman_filter / kalman_smoother specs.

Leading-underscore filename marks this as spec-internal (not a
registered spec). The state-space family now has a shared helper
module per the future-promotion convention: the second distinct
wrapper to need these helpers (kalman_smoother after kalman_filter)
warrants extraction.

Exports:
  - ``render_state_space_tier1_skeleton`` — shared Tier 1 preamble
    combining wrapper kind (filter/smoother), series name, state
    dimension, template name, n_obs, initialization.
  - ``render_final_state_summary`` — "At period T the filtered level
    is X (SE Y)" clause.
  - ``render_filter_vs_smoother_disclosure`` — Tier 2 paragraph
    explaining online (filter) vs retrospective (smoother)
    estimation and what each state table represents.
  - ``render_initialization_disclosure`` — Tier 2 sentence on diffuse
    vs known init.
  - ``render_model_equations`` — state-equations block for template
    path (y_t = μ_t + ε_t, etc.), per template.
  - ``render_custom_matrix_disclosure`` — Tier 2 block for the custom
    path stating user-supplied matrix shapes and the "no free
    parameters" framing.
  - ``format_state_shape_summary`` — "2-dim state: [level, slope]"
    summary fragment.
  - Shared Tier 3 triggers: ``_trigger_jb_nonnormal``,
    ``_trigger_lb_residual_ac``, ``_trigger_rmse_exceeds_baseline``,
    ``_trigger_convergence_warning``, ``_trigger_custom_path_no_mle``.

Follow-up 2a Decision 5: matrix serialization uses ``np.asarray``
with explicit shape validation — see ``_kalman_common._validate_
matrix_shapes`` on the wrapper side.

Follow-up 2a Decision 8 framing: the custom path positions as an
*inference* tool, not an estimation tool. Per Phase 2 feedback: "This
mode is intended for users who have already determined their state-
space matrices through prior estimation (in another tool or via
theoretical reasoning) and want TSL to perform the state inference.
For matrix estimation, use the template path with MLE."
"""

from typing import Optional

from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)


# ---------------------------------------------------------------------
# Tier 1 helpers
# ---------------------------------------------------------------------


def render_state_space_tier1_skeleton(results: dict, wrapper_kind: str) -> str:
    """Return the shared Tier 1 preamble fragment.

    Pattern:
        "Kalman {filter|smoother} applied to <series_name> with <k>-dim
         state (<state_labels>) under the <template> model, over <n>
         observations with <initialization> initialization."
    """
    series_name = str(results.get("series_name", "the series"))
    state_dim = int(results.get("state_dim", 0))
    state_labels = results.get("state_labels") or []
    template = str(results.get("state_space_model", "local_level"))
    n = int(results.get("n_obs", 0))
    initialization = str(results.get("initialization", "diffuse"))

    label_fragment = ""
    if state_labels:
        if len(state_labels) == 1:
            label_fragment = f" ({state_labels[0]})"
        elif len(state_labels) <= 4:
            label_fragment = f" ({', '.join(state_labels)})"
        else:
            # Long seasonal state vectors: summarize rather than list all
            label_fragment = (
                f" ({state_labels[0]} + {len(state_labels) - 1} seasonal)"
            )

    template_phrase = _template_display_phrase(template, results)
    verb = "applied to"
    kind_label = "Kalman filter" if wrapper_kind == "filter" \
        else "Kalman smoother"

    # Custom path discloses "known" init is user-supplied
    init_phrase = (
        f"user-supplied known initialization"
        if initialization == "known" and template == "custom"
        else f"{initialization} initialization"
    )

    return (
        f"{kind_label} {verb} {format_series_reference(series_name)} "
        f"with {state_dim}-dim state{label_fragment} under the "
        f"{template_phrase}, over {n} observations with {init_phrase}."
    )


def _template_display_phrase(template: str, results: dict) -> str:
    """Human-readable name for a template value."""
    if template == "local_level":
        return "local-level model"
    if template == "local_linear_trend":
        return "local-linear-trend model"
    if template == "seasonal":
        p = results.get("seasonal_period")
        if p:
            return f"seasonal model (period {int(p)})"
        return "seasonal model"
    if template == "ar1":
        return "AR(1)-state model"
    if template == "custom":
        return "custom linear-Gaussian state-space model with user-supplied matrices"
    return f"{template} model"


def render_final_state_summary(results: dict, wrapper_kind: str) -> str:
    """Render "At period T the <kind> <label> is X (SE Y)" fragment.

    Picks the first state dimension as the "dominant" (level, for
    templates; state_0 for custom). For local_linear_trend, renders
    both level and slope since slope is a key second-order quantity.
    """
    if wrapper_kind == "filter":
        state = results.get("filter_final_state") or {}
        state_se = results.get("filter_final_state_se") or {}
        kind_word = "filtered"
    else:
        state = results.get("smoother_final_state") or {}
        state_se = results.get("smoother_final_state_se") or {}
        kind_word = "smoothed"

    if not state:
        return ""

    state_labels = results.get("state_labels") or list(state.keys())
    template = str(results.get("state_space_model", ""))

    # For local_linear_trend, render both level and slope
    if template == "local_linear_trend" and "level" in state and "slope" in state:
        level_v = state.get("level")
        level_se = state_se.get("level")
        slope_v = state.get("slope")
        slope_se = state_se.get("slope")
        if level_v is None or slope_v is None:
            return ""
        return (
            f"At period T the {kind_word} level is "
            f"{format_scale_aware(float(level_v))} and the {kind_word} "
            f"slope is {format_scale_aware(float(slope_v))} "
            f"(SE {format_scale_aware(float(level_se or 0.0))}, "
            f"{format_scale_aware(float(slope_se or 0.0))})."
        )

    # General: report the first state dimension
    if state_labels and state_labels[0] in state:
        label = state_labels[0]
    else:
        label = next(iter(state.keys()))
    val = state.get(label)
    se = state_se.get(label)
    if val is None:
        return ""
    return (
        f"At period T the {kind_word} {label} is "
        f"{format_scale_aware(float(val))} "
        f"(SE {format_scale_aware(float(se or 0.0))})."
    )


def format_state_shape_summary(results: dict) -> str:
    """Return "<k>-dim state: [<label1>, <label2>, ...]" fragment."""
    state_dim = int(results.get("state_dim", 0))
    labels = results.get("state_labels") or []
    if not labels:
        return f"{state_dim}-dim state"
    if len(labels) <= 5:
        return f"{state_dim}-dim state: [{', '.join(labels)}]"
    return (
        f"{state_dim}-dim state: [{labels[0]}, ...{len(labels) - 1} more]"
    )


# ---------------------------------------------------------------------
# Tier 2 helpers
# ---------------------------------------------------------------------


def render_filter_vs_smoother_disclosure(wrapper_kind: str) -> str:
    """Return the Tier 2 paragraph explaining filter vs smoother.

    Critical distinction: filter uses y_{1:t}, smoother uses y_{1:T}.
    """
    if wrapper_kind == "filter":
        return (
            "The Kalman filter produces online one-step-ahead state "
            "estimates conditioned on observations y_{1:t} — each "
            "period's filtered state reflects information up to and "
            "including that period but NOT future observations. This "
            "contrasts with the smoother (kalman_smoother), which "
            "uses the full sample y_{1:T} retrospectively. The "
            "filtered state is the right quantity for real-time / "
            "streaming inference; for historical analysis and shock "
            "attribution, use the smoother."
        )
    return (
        "The Kalman smoother produces retrospective state estimates "
        "conditioned on the full sample y_{1:T}, whereas the filter "
        "produces online estimates conditioned on y_{1:t} only. "
        "Smoothed estimates are always at least as precise as filtered "
        "ones (SE_smoothed ≤ SE_filtered) and typically produce the "
        "largest revisions at early periods — before the filter had "
        "accumulated much information. Use the smoother for historical "
        "analysis; use the filter for real-time inference."
    )


def render_initialization_disclosure(results: dict) -> str:
    """Return one sentence on diffuse vs known initialization."""
    init = str(results.get("initialization", "diffuse"))
    template = str(results.get("state_space_model", ""))
    if init == "known":
        if template == "custom":
            return (
                "Known initialization with user-supplied initial state "
                "and covariance — the filter does not use a diffuse "
                "prior on the custom path."
            )
        return (
            "Known initialization with user-supplied initial state and "
            "covariance."
        )
    if init == "approximate_diffuse":
        return (
            "Approximate diffuse initialization (large prior variance). "
            "Early-period filtered states depend on the initialization "
            "until the Kalman gain has propagated several observations."
        )
    return (
        "Diffuse initialization (statsmodels default). Early-period "
        "filtered states depend on the init until the Kalman gain has "
        "propagated several observations; the smoother revises these "
        "early estimates retrospectively."
    )


def render_model_equations(template: str, results: dict) -> str:
    """Return the state-equation block for a template path."""
    if template == "local_level":
        return (
            "State-space equations: y_t = μ_t + ε_t, μ_t = μ_{t-1} + "
            "η_t, with ε_t ~ N(0, σ²_ε) and η_t ~ N(0, σ²_η). "
            "Random-walk level (1 state) plus observation noise."
        )
    if template == "local_linear_trend":
        return (
            "State-space equations: y_t = μ_t + ε_t, μ_t = μ_{t-1} + "
            "β_{t-1} + η_t, β_t = β_{t-1} + ζ_t, with ε_t ~ N(0, σ²_ε), "
            "η_t ~ N(0, σ²_η), ζ_t ~ N(0, σ²_ζ). Two latent states "
            "(level μ_t, slope β_t) evolving as a random walk with "
            "drift; the slope itself is a random walk."
        )
    if template == "seasonal":
        p = results.get("seasonal_period", 12)
        return (
            f"State-space equations: y_t = μ_t + γ_t + ε_t, with γ_t "
            f"enforcing Σ_{{j=0..{int(p) - 1}}} γ_{{t-j}} = 0 (sum-to-"
            f"zero seasonality of period {int(p)}). State vector "
            f"combines the level and {int(p) - 1} linearly independent "
            f"seasonal indicators. Seasonality is additive."
        )
    if template == "ar1":
        return (
            "State-space equations: y_t = α + s_t + ε_t, s_t = φ "
            "s_{t-1} + η_t, with ε_t ~ N(0, σ²_ε) and η_t ~ N(0, σ²_η). "
            "Fixed-intercept α plus an AR(1) state s_t; the AR "
            "coefficient φ is estimated by MLE."
        )
    return ""


def render_custom_matrix_disclosure(results: dict) -> str:
    """Return the Tier 2 block for custom-path runs.

    Discloses matrix shapes, zero-free-parameter framing, and the
    Phase 2 feedback framing that positions this as an inference-only
    tool (not an estimation tool).
    """
    shapes = results.get("custom_matrix_shapes") or {}
    if not shapes:
        return (
            "Custom linear-Gaussian state-space model with user-supplied "
            "matrices. No free parameters are estimated — the filter "
            "evaluates at the fixed matrices and extracts the state "
            "trajectory."
        )

    def _shape(key):
        s = shapes.get(key)
        if s and len(s) == 2:
            return f"{key} ({int(s[0])}×{int(s[1])})"
        if s and len(s) == 1:
            return f"{key} ({int(s[0])},)"
        return key

    shape_parts = ", ".join([
        _shape("Z"), _shape("T"), _shape("R"),
        _shape("H"), _shape("Q"),
    ])
    return (
        f"User-specified linear-Gaussian state-space model: y_t = Z s_t "
        f"+ ε_t, s_t = T s_{{t-1}} + R η_t, with user-supplied matrices "
        f"{shape_parts}. No free parameters are estimated — the filter "
        f"evaluates at the fixed user matrices and extracts the state "
        f"trajectory. This makes the wrapper a pure inference tool "
        f"rather than an estimation tool on the custom path. This mode "
        f"is intended for users who have already determined their "
        f"state-space matrices through prior estimation (in another "
        f"tool or via theoretical reasoning) and want TSL to perform "
        f"the state inference. For matrix estimation, use the template "
        f"path with MLE."
    )


def render_likelihood_summary(results: dict) -> str:
    """Return "Log-likelihood X, AIC Y, BIC Z on N free parameters" fragment.

    For custom path (n_free_params=0), notes that AIC/BIC are
    degenerate but emitted for parity.
    """
    llf = results.get("log_likelihood")
    aic = results.get("aic")
    bic = results.get("bic")
    k = results.get("n_free_params")
    template = str(results.get("state_space_model", ""))

    parts = []
    if llf is not None:
        parts.append(f"log-likelihood {format_scale_aware(float(llf))}")
    if aic is not None:
        parts.append(f"AIC {format_scale_aware(float(aic))}")
    if bic is not None:
        parts.append(f"BIC {format_scale_aware(float(bic))}")

    if not parts:
        return ""

    core = ", ".join(parts)
    if template == "custom" and k == 0:
        return (
            f"{core} on 0 free parameters (custom path — AIC and BIC "
            f"degenerate, reported for parity only)."
        )
    if k is not None:
        return f"{core} on {int(k)} free parameter{'s' if k != 1 else ''}."
    return f"{core}."


def render_variance_components(results: dict) -> str:
    """Return variance-component disclosure for the template path.

    Only relevant when sigma_obs / sigma_level / sigma_slope are
    present (set by template-path wrappers).
    """
    s_obs = results.get("sigma_obs")
    s_lvl = results.get("sigma_level")
    s_slp = results.get("sigma_slope")
    q = results.get("q_ratio")

    parts = []
    if s_obs is not None:
        parts.append(f"σ²_ε = {format_scale_aware(float(s_obs))}")
    if s_lvl is not None:
        parts.append(f"σ²_η = {format_scale_aware(float(s_lvl))}")
    if s_slp is not None:
        parts.append(f"σ²_ζ = {format_scale_aware(float(s_slp))}")

    if not parts:
        return ""

    head = "MLE yielded " + ", ".join(parts)
    if q is not None:
        q_band = _q_band(float(q))
        return f"{head} (signal-to-noise ratio q = {format_scale_aware(float(q))}, {q_band})."
    return head + "."


def _q_band(q: float) -> str:
    if q < 0.01:
        return "very low"
    if q < 0.1:
        return "low"
    if q < 1.0:
        return "moderate"
    if q < 10.0:
        return "high"
    return "very high"


def render_residual_diagnostics(results: dict) -> str:
    """Return "Residual diagnostics: JB p=..., LB-10 p=..., DW=..." fragment."""
    jb = results.get("jarque_bera_pvalue")
    lb = results.get("ljung_box_lag10_pvalue")
    dw = results.get("durbin_watson")
    parts = []
    if jb is not None:
        parts.append(f"JB p = {format_scale_aware(float(jb))}")
    if lb is not None:
        parts.append(f"LB-10 p = {format_scale_aware(float(lb))}")
    if dw is not None:
        parts.append(f"DW {format_scale_aware(float(dw))}")
    if not parts:
        return ""
    return "Residual diagnostics: " + ", ".join(parts) + "."


# ---------------------------------------------------------------------
# Shared Tier 3 triggers
# ---------------------------------------------------------------------


def _trigger_jb_nonnormal(results: dict) -> Optional[str]:
    """Fires when Jarque-Bera p < 0.05 (residuals non-normal)."""
    jb = results.get("jarque_bera_pvalue")
    if jb is None or float(jb) >= 0.05:
        return None
    p_str = "p<0.0001" if float(jb) < 1e-4 \
        else f"p={format_scale_aware(float(jb))}"
    return (
        f"Residual normality test rejects at the 5% level (JB {p_str}); "
        f"the Gaussian state-space assumption may not hold on this "
        f"series. Prediction intervals and credible-band coverage may "
        f"be mis-calibrated in the tails. Consider a heavier-tailed "
        f"specification (Student-t innovations) or bootstrapped "
        f"intervals."
    )


def _trigger_lb_residual_ac(results: dict) -> Optional[str]:
    """Fires when Ljung-Box lag-10 p < 0.05 (residual autocorrelation)."""
    lb = results.get("ljung_box_lag10_pvalue")
    if lb is None or float(lb) >= 0.05:
        return None
    p_str = "p<0.0001" if float(lb) < 1e-4 \
        else f"p={format_scale_aware(float(lb))}"
    return (
        f"Residual autocorrelation detected at lag 10 (Ljung-Box {p_str}); "
        f"the model leaves temporal structure in the residuals. Consider "
        f"adding an AR component (ar1 template) or switching to a "
        f"richer template (local_linear_trend or seasonal)."
    )


def _trigger_rmse_exceeds_baseline(results: dict) -> Optional[str]:
    """Fires when fit_rmse >= baseline_rmse (no improvement over naive)."""
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None or float(base) <= 0:
        return None
    if float(fit) < float(base):
        return None
    label = str(results.get("baseline_label", "naive"))
    return (
        f"Fit RMSE {format_scale_aware(float(fit))} matches or exceeds "
        f"the {label} baseline's {format_scale_aware(float(base))}. The "
        f"state-space model does not beat naive on this series; a "
        f"constant-forecast baseline is competitive. Consider a richer "
        f"template or a different model family (ARIMA, structural_ts)."
    )


def _trigger_convergence_warning(results: dict) -> Optional[str]:
    """Fires on non-converged MLE fit (template path only — custom
    path always reports converged=True)."""
    converged = results.get("converged")
    template = str(results.get("state_space_model", ""))
    if template == "custom" or converged is None or bool(converged):
        return None
    return (
        "MLE optimizer did not fully converge. Variance-component "
        "estimates and their credible bands may be approximate. Try "
        "increasing maxiter (Thorough preset) or switching to a simpler "
        "template."
    )


def _trigger_custom_path_no_mle(results: dict) -> Optional[str]:
    """Always fires on custom-path runs (disclosure trigger)."""
    template = str(results.get("state_space_model", ""))
    if template != "custom":
        return None
    return (
        "Custom path — no MLE fit: this run evaluated the Kalman "
        "operation at user-supplied matrices rather than estimating "
        "variance parameters. Reported log-likelihood reflects the "
        "user's matrix choices; AIC and BIC are degenerate (k=0 free "
        "parameters) and reported for parity only. If a mis-specified "
        "matrix produces a poor fit, the wrapper still runs but the "
        "state estimates may be unreliable — cross-check residual RMSE "
        "against alternative matrix choices, or switch to a template "
        "path for MLE-driven parameter estimation."
    )
