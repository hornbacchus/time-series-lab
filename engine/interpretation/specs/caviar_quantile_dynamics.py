"""
InterpretationSpec for caviar_quantile_dynamics (Conditional
Autoregressive Value-at-Risk — Engle & Manganelli 2004).

Stand-alone Tier 1 shape — quantile-forecast-with-backtest. Distinct
from GARCH (models variance, not quantile directly), EVT (fits tail
distribution, not dynamic quantile), and C2 forecasters (point
forecast, not quantile).

Decision D7: Tier 2 opening sentence makes distribution-free framing
explicit per Convention C.
Decision D8: Tier 1 backtest ordering — Kupiec first, then DQ
(Engle-Manganelli); Christoffersen relegated to Tier 2 / Tier 3.
Decision D17: Christoffersen referenced as "conditional coverage
test" (not "independence test"); DQ as "Engle-Manganelli Dynamic
Quantile joint test".

Results-dict keys consumed:

    series_name / n_obs
    specification (SAV / AS / IG) / theta / parameter_names / parameters
    quantile_loss
    n_violations / expected_violations / violation_ratio
    kupiec_stat / kupiec_pval
    christoffersen_stat / christoffersen_pval
    dq_stat / dq_pval
    distribution_free

Follow-up 3a adds forecast capability (wrapper previously emitted no
explicit forecasts at all):

    one_step_ahead_var                — q_{T+1|T} explicit 1-step VaR
    multi_step_computed               — bool
    horizons_forecasted               — list[int]
    multi_step_quantiles              — dict[h, VaR]
    multi_step_mc_paths               — N simulation paths
    multi_step_mc_noise_std           — dict[h, MC std error]
    multi_step_residual_autocorr_lbq  — Ljung-Box p on residuals
    caviar_stationarity_param         — β₁
    caviar_effective_persistence      — β₁ + max(|β_i|, ...) per spec
    caviar_stationarity_ok            — bool
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_COEF_SIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _fmt_confidence_from_theta(theta: float) -> str:
    """Convention A: the 'confidence level' for VaR is (1 − θ) · 100%.
    Integer when whole (θ = 0.05 → 95%), fractional otherwise (θ =
    0.005 → 99.5%)."""
    try:
        conf = (1.0 - float(theta)) * 100.0
    except Exception:
        return f"{theta}"
    if abs(conf - round(conf)) < 1e-9:
        return f"{int(round(conf))}%"
    return f"{conf:.1f}%"


def _fmt_theta_pct(theta: float) -> str:
    try:
        v = float(theta) * 100.0
    except Exception:
        return f"{theta}"
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}%"
    return f"{v:.1f}%"


_SPEC_FULL_NAME = {
    "SAV": "Symmetric Absolute Value",
    "AS": "Asymmetric Slope",
    "IG": "Indirect GARCH",
}


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the return series"))
    n = int(results.get("n_obs", 0))
    spec = str(results.get("specification", "SAV")).upper()
    spec_full = _SPEC_FULL_NAME.get(spec, spec)
    theta = results.get("theta", 0.05)
    conf_str = _fmt_confidence_from_theta(theta)
    theta_pct = _fmt_theta_pct(theta)

    n_viol = int(results.get("n_violations", 0))
    exp_viol = results.get("expected_violations")
    try:
        exp_viol_f = float(exp_viol) if exp_viol is not None else float(n) * float(theta)
        exp_viol_str = f"{exp_viol_f:.1f}"
    except Exception:
        exp_viol_f = None
        exp_viol_str = "n/a"

    v_ratio = results.get("violation_ratio")
    try:
        v_ratio_str = f"{float(v_ratio):.2f}" if v_ratio is not None else "n/a"
    except Exception:
        v_ratio_str = "n/a"

    kupiec_p = results.get("kupiec_pval")
    dq_p = results.get("dq_pval")
    kupiec_clause = ""
    if kupiec_p is not None:
        try:
            verdict = (
                "does not reject"
                if float(kupiec_p) >= 0.05
                else "rejects"
            )
            kupiec_clause = (
                f"Kupiec unconditional coverage test {verdict} "
                f"(p = {FMT_P_VALUE.format(float(kupiec_p))})."
            )
        except Exception:
            kupiec_clause = ""
    dq_clause = ""
    if dq_p is not None:
        try:
            verdict = (
                "does not reject"
                if float(dq_p) >= 0.05
                else "rejects"
            )
            dq_clause = (
                f" Dynamic Quantile (Engle-Manganelli 2004) joint test "
                f"{verdict} (p = {FMT_P_VALUE.format(float(dq_p))})."
            )
        except Exception:
            dq_clause = ""

    # Coverage descriptor (mirrors wrapper convention).
    coverage_desc = ""
    try:
        vr = float(v_ratio) if v_ratio is not None else None
        if vr is not None:
            if vr < 0.8:
                coverage_desc = "too conservative (fewer violations than expected)"
            elif vr > 1.2:
                coverage_desc = "too aggressive (more violations than expected)"
            else:
                coverage_desc = "well-calibrated at the unconditional coverage level"
    except Exception:
        pass
    cov_phrase = f" — {coverage_desc}" if coverage_desc else ""

    # Follow-up 3a — multi-horizon VaR closing clause
    mh_q = results.get("multi_step_quantiles") or {}
    multi_step_computed = bool(results.get("multi_step_computed", False))
    mh_closer = ""
    if multi_step_computed and mh_q:
        horizon_parts = []
        for h in sorted(int(k) for k in mh_q.keys()):
            try:
                horizon_parts.append(f"{int(h)}-step = {float(mh_q[h]):.4f}")
            except Exception:
                continue
        if horizon_parts:
            mh_closer = (
                f" Multi-horizon {conf_str} VaR at "
                f"{', '.join(horizon_parts)} (via Monte Carlo bootstrap; "
                f"see Multi-Horizon VaR Forecasts table for MC standard "
                f"errors and 90% bands)."
            )

    return (
        f"CAViaR {spec} ({spec_full}) dynamic quantile model at the "
        f"{conf_str} VaR level ({theta_pct} quantile) on "
        f"{format_series_reference(name)} ({n} daily observations). "
        f"{n_viol} violations observed vs {exp_viol_str} expected "
        f"(realized / nominal exceedance ratio {v_ratio_str}"
        f"{cov_phrase}). {kupiec_clause}{dq_clause} The Christoffersen "
        f"conditional coverage test is flagged separately in Tier 3."
        f"{mh_closer}"
    )


def _tier2(results: dict) -> str:
    spec = str(results.get("specification", "SAV")).upper()
    spec_full = _SPEC_FULL_NAME.get(spec, spec)
    theta = results.get("theta", 0.05)

    pnames = list(results.get("parameter_names") or [])
    pvals = list(results.get("parameters") or [])

    # Parameter disclosure — align names with values by position.
    param_clauses = []
    for nm, v in zip(pnames, pvals):
        try:
            param_clauses.append(
                f"{nm} = {FMT_COEF_SIGNED.format(float(v))}"
            )
        except Exception:
            continue
    params_str = ", ".join(param_clauses) if param_clauses else "parameters unavailable"

    qloss = results.get("quantile_loss")
    qloss_str = format_scale_aware(float(qloss)) if qloss is not None else "n/a"

    kupiec_p = results.get("kupiec_pval")
    cc_p = results.get("christoffersen_pval")
    dq_p = results.get("dq_pval")

    def _verdict(p, reject_text="rejects", accept_text="does not reject"):
        if p is None:
            return "unavailable"
        try:
            return reject_text if float(p) < 0.05 else accept_text
        except Exception:
            return "unavailable"

    backtests_clause = (
        f"Kupiec unconditional coverage "
        f"(p = {FMT_P_VALUE.format(float(kupiec_p))}, "
        f"{_verdict(kupiec_p)}); Christoffersen conditional coverage "
        f"via first-order Markov chain on the hit indicators "
        f"(p = {FMT_P_VALUE.format(float(cc_p))}, "
        f"{_verdict(cc_p)}); Engle-Manganelli Dynamic Quantile joint "
        f"test (p = {FMT_P_VALUE.format(float(dq_p))}, "
        f"{_verdict(dq_p)})."
        if all(x is not None for x in (kupiec_p, cc_p, dq_p))
        else "Backtest p-values unavailable for one or more tests."
    )

    # Specification-specific color.
    spec_color = ""
    if spec == "SAV":
        spec_color = (
            " SAV: q_t = β₀ + β₁ · q_{t−1} + β₂ · |y_{t−1}| — symmetric "
            "response to positive and negative lagged returns. Does not "
            "capture leverage effects; consider the Asymmetric Slope "
            "(AS) variant if negative returns should widen VaR more "
            "than positive returns."
        )
    elif spec == "AS":
        spec_color = (
            " AS: q_t = β₀ + β₁ · q_{t−1} + β₂ · y_{t−1}^+ + β₃ · "
            "y_{t−1}^− — asymmetric response separates positive and "
            "negative lagged returns, capturing leverage-effect "
            "dynamics."
        )
    elif spec == "IG":
        spec_color = (
            " IG: q_t derived from an indirect GARCH(1,1) variance "
            "process — quantile implied by variance dynamics but fit "
            "directly via quantile loss rather than likelihood."
        )

    # Variant-specific follow-up suggestion — don't suggest refitting
    # with the variant we're already using.
    if spec == "SAV":
        followup = (
            " For a leverage-aware check on the dynamic response, "
            "refit with the Asymmetric Slope (AS) variant."
        )
    elif spec == "AS":
        followup = (
            " For a symmetric-response check (no leverage asymmetry), "
            "compare against the Symmetric Absolute Value (SAV) "
            "variant."
        )
    else:  # IG
        followup = (
            " For a direct-quantile check independent of the variance "
            "process, compare against the Symmetric Absolute Value "
            "(SAV) variant."
        )

    # Follow-up 3a — framing correction paragraph (honestly
    # acknowledges the prior state rather than rewriting C6
    # disclosure ahistorically, per user Phase 1 review feedback).
    framing_paragraph = (
        " Prior to this capability extension, the wrapper emitted "
        "no explicit forecasts — only the in-sample quantile path "
        "and backtests. Users wanting operational VaR had to extract "
        "the final in-sample quantile themselves. This capability "
        "adds explicit 1-step-ahead VaR (q_{T+1|T}) as a first-class "
        "output plus multi-horizon VaR via Monte Carlo bootstrap "
        "simulation at user-specified horizons."
    )

    one_step = results.get("one_step_ahead_var")
    one_step_clause = (
        f" 1-step-ahead VaR q_{{T+1|T}} = {float(one_step):.4f}."
        if one_step is not None else ""
    )

    n_paths = results.get("multi_step_mc_paths")
    horizons_list = results.get("horizons_forecasted") or []
    methodology_paragraph = ""
    limitations_paragraph = ""
    if horizons_list and n_paths is not None:
        try:
            horizons_str = ", ".join(
                str(int(h)) for h in sorted(horizons_list)
            )
            methodology_paragraph = (
                f" Multi-horizon VaR computed via Monte Carlo "
                f"bootstrap simulation at horizons "
                f"{{{horizons_str}}} with {int(n_paths):,} forward "
                f"paths. Each path simulates y_{{T+h}} by bootstrap-"
                f"resampling raw residuals r_t = y_t − q_t "
                f"(preserves empirical CDF; Christoffersen 2012), "
                f"propagating the CAViaR recursion for q_{{T+h+1|T+h}}. "
                f"The θ-quantile of simulated y values at each "
                f"horizon is the multi-horizon VaR; 5% / 95% "
                f"percentiles provide the 90% band. Monte Carlo "
                f"noise is estimated by sub-sample bootstrap of the "
                f"quantile estimator (B = 50 subsamples)."
            )
            limitations_paragraph = (
                " Three methodological caveats: (a) deep-tail MC "
                "quantiles at finite N have material Monte Carlo "
                "noise — see the MC Std Error column in the "
                "Multi-Horizon VaR Forecasts table, and Tier 3 D1 "
                "when noise exceeds 10% of the quantile estimate; "
                "(b) bootstrap iid-resampling assumes residuals are "
                "exchangeable, which Tier 3 D2 flags via Ljung-Box "
                "on r_t; (c) multi-horizon requires CAViaR dynamical "
                "stability (effective persistence β₁ + max(|β_k|) < 1 "
                "for SAV / AS, β₁ + β₂ < 1 for IG); Tier 3 D3 fires "
                "when the condition fails. D3 uses a conservative "
                "worst-case bound — the simulation may stay "
                "empirically bounded even when D3 fires (compare "
                "MC Std Error for diagnostic)."
            )
        except Exception:
            methodology_paragraph = ""
            limitations_paragraph = ""

    # Convention C — distribution-free opening.
    return (
        f"CAViaR is distribution-free: the quantile loss "
        f"(check / pinball function) "
        f"L(y, q; θ) = (y − q)(θ − 𝟙[y < q]) makes no assumption "
        f"about the return distribution — unlike GARCH-based VaR "
        f"(parametric) or EVT (tail-parametric). Fit by Nelder-Mead "
        f"minimization of the empirical quantile loss with random "
        f"restarts (preset-gated). Specification {spec} ({spec_full}) "
        f"at quantile θ = {theta}: {params_str}. Minimized quantile "
        f"loss = {qloss_str}.{spec_color} **Backtests:** "
        f"{backtests_clause}{followup}{framing_paragraph}"
        f"{one_step_clause}{methodology_paragraph}"
        f"{limitations_paragraph}"
    )


def _trigger_kupiec_rejects(results: dict) -> Optional[str]:
    p = results.get("kupiec_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Kupiec unconditional coverage test rejects at the 5% level "
        f"(p = {FMT_P_VALUE.format(float(p))}). Realized exceedance "
        f"rate differs materially from the nominal rate; the quantile "
        f"level is miscalibrated on this sample. Consider an "
        f"alternative CAViaR specification or widen the optimization "
        f"restart count."
    )


def _trigger_christoffersen_rejects(results: dict) -> Optional[str]:
    p = results.get("christoffersen_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Christoffersen conditional coverage test rejects at the 5% "
        f"level (p = {FMT_P_VALUE.format(float(p))}); violations are "
        f"clustered, not independent. Unconditional coverage may be "
        f"correct (see Kupiec separately) but the pattern of "
        f"exceedances shows serial dependence — the model's dynamic "
        f"response is too slow to adjust the quantile after a "
        f"violation. Consider the Asymmetric Slope (AS) variant, "
        f"which separates leverage-effect responses to positive vs "
        f"negative lagged returns."
    )


def _trigger_dq_rejects(results: dict) -> Optional[str]:
    p = results.get("dq_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Dynamic Quantile (Engle-Manganelli 2004) joint test rejects "
        f"at the 5% level (p = {FMT_P_VALUE.format(float(p))}); the "
        f"model is neither well-calibrated nor adequate on the joint "
        f"coverage-and-independence criterion. Consider an alternative "
        f"CAViaR specification (AS for leverage; IG for "
        f"variance-linked dynamics) or increase the optimization "
        f"restart count (Thorough preset)."
    )


# ---------------------------------------------------------------------
# Follow-up 3a — Multi-horizon Tier 3 triggers
# ---------------------------------------------------------------------


def _trigger_mc_noise_warning(results: dict) -> Optional[str]:
    """D1 — fires when MC noise std at the longest horizon exceeds
    10% of the (absolute) quantile estimate. Signals that the
    tail-quantile estimate at the deepest horizon is noisy at the
    current N; user should increase n_simulation_paths."""
    if not bool(results.get("multi_step_computed", False)):
        return None
    horizons = results.get("horizons_forecasted") or []
    if not horizons:
        return None
    try:
        h_longest = max(int(h) for h in horizons)
    except Exception:
        return None
    mh_q = results.get("multi_step_quantiles") or {}
    mh_noise = results.get("multi_step_mc_noise_std") or {}
    if h_longest not in mh_q or h_longest not in mh_noise:
        return None
    try:
        VaR_h = float(mh_q[h_longest])
        noise_h = float(mh_noise[h_longest])
    except Exception:
        return None
    if abs(VaR_h) < 1e-12:
        return None
    noise_ratio = noise_h / abs(VaR_h)
    if noise_ratio < 0.10:
        return None
    n_paths = results.get("multi_step_mc_paths")
    n_paths_str = f"{int(n_paths):,}" if n_paths is not None else "unknown"
    return (
        f"Monte Carlo standard error at horizon {h_longest} is "
        f"{noise_ratio:.1%} of the quantile estimate "
        f"({format_scale_aware(VaR_h)} ± "
        f"{format_scale_aware(noise_h)}) — the longest-horizon tail "
        f"is noisy. Increase n_simulation_paths (currently "
        f"{n_paths_str}) via the Thorough preset to reduce noise."
    )


def _trigger_residual_autocorr_caviar(results: dict) -> Optional[str]:
    """D2 — fires when in-sample residuals show autocorrelation
    (Ljung-Box p < 0.05). Bootstrap iid resampling assumes
    exchangeability; residual dependence mis-calibrates the
    simulation."""
    if not bool(results.get("multi_step_computed", False)):
        return None
    p = results.get("multi_step_residual_autocorr_lbq")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"CAViaR residuals show autocorrelation at lag 10 "
        f"(Ljung-Box p = {FMT_P_VALUE.format(float(p))}). The "
        f"multi-horizon bootstrap resamples residuals iid; residual "
        f"dependence mis-calibrates the simulated VaR paths. "
        f"Consider fitting a richer CAViaR variant (SAV → AS "
        f"captures leverage asymmetry; AS → IG captures "
        f"variance-implied dynamics) or — backlog — block bootstrap "
        f"for residual dependence."
    )


def _trigger_caviar_non_stationary(results: dict) -> Optional[str]:
    """D3 — fires when CAViaR effective persistence fails the
    stability condition for multi-horizon bootstrap. Conservative
    worst-case bound: the simulation may stay empirically bounded
    even when this fires (check MC Std Error in the Multi-Horizon
    table to diagnose)."""
    ok = results.get("caviar_stationarity_ok")
    if ok is None or bool(ok):
        return None
    eff = results.get("caviar_effective_persistence")
    beta_1 = results.get("caviar_stationarity_param")
    if eff is None or beta_1 is None:
        return None
    spec = str(results.get("specification", "")).upper()
    if spec == "IG":
        cond_str = "β₁ + β₂ < 1 (and β₁ ≥ 0)"
    elif spec == "AS":
        cond_str = "β₁ + max(|β₂|, |β₃|) < 1"
    else:
        cond_str = "β₁ + |β₂| < 1"
    return (
        f"CAViaR effective persistence "
        f"{FMT_COEF_SIGNED.format(float(eff))} "
        f"(β₁ = {FMT_COEF_SIGNED.format(float(beta_1))}) fails the "
        f"multi-horizon stability condition {cond_str}. The bootstrap "
        f"recursion may diverge as horizon grows because |y| feeds "
        f"back into |q|; long-horizon VaR values in the Multi-"
        f"Horizon VaR Forecasts table may be unreliable. This is a "
        f"conservative worst-case bound — the AS variant in "
        f"particular can stay empirically bounded under sign-"
        f"asymmetric residual dynamics even when this check fails. "
        f"Inspect the MC Std Error column to diagnose whether the "
        f"simulation actually diverged. Consider re-specifying "
        f"(switch variant or check for outliers) or restricting "
        f"forecasts to the 1-step-ahead VaR only."
    )


SPEC = InterpretationSpec(
    technique_id="caviar_quantile_dynamics",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_kupiec_rejects,
        _trigger_christoffersen_rejects,
        _trigger_dq_rejects,
        # Follow-up 3a — Multi-horizon triggers:
        _trigger_mc_noise_warning,
        _trigger_residual_autocorr_caviar,
        _trigger_caviar_non_stationary,
    ),
    mode_aware=False,
)

register(SPEC)
