"""
InterpretationSpec for har_cj (HAR-CJ jumps-aware realized
volatility — Andersen, Bollerslev & Diebold 2007).

Distinct from HAR-RV (Corsi 2009) in the Tier 1 shape:
HAR-RV uses the forecaster-family cascade-summary Tier 1 with a
dominant-component color. HAR-CJ adds a continuous-vs-jump
persistence contrast as its signature Tier 1 phrase — the central
empirical finding of ABD 2007 that jumps have near-zero
persistence while continuous volatility is highly persistent.

HAR-RV's D19 low-R² trigger already references "jumps-aware
variants like HAR-CJ" as a recommended extension. 3b fulfills
that cross-reference; no HAR-RV spec change needed.

Results-dict keys consumed:

    series_name / n_obs / n_obs_raw
    model (HAR-CJ or log-HAR-CJ) / use_log
    daily_lag / weekly_lag / monthly_lag / h_ahead
    M_sampling_frequency / jump_alpha / jump_detection_threshold
    jump_days_count / jump_days_fraction
    mean_jump_contribution / mean_continuous_contribution
    bns_test_statistic_max / tq_approximated
    beta_0 / beta_cd / beta_cw / beta_cm / beta_jd / beta_jw / beta_jm
    beta_jd_pvalue / beta_jw_pvalue / beta_jm_pvalue
    continuous_persistence_sum / jump_persistence_sum
    R2 / R2_adj / aic / bic
    fit_rmse / baseline_rmse / baseline_label
    forecast_end_value / last_observed_value / series_mean / series_std
    ljung_box_lag10_pvalue / jarque_bera_pvalue
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_COEF_SIGNED,
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
    name = str(results.get("series_name", "the RV series"))
    n = int(results.get("n_obs", 0))
    n_raw = int(results.get("n_obs_raw", n))
    h = int(results.get("h_ahead", 1) or 1)
    horizon_phrase = f"{h} period" if h == 1 else f"{h} periods"

    n_jumps = int(results.get("jump_days_count", 0))
    jump_frac = results.get("jump_days_fraction")
    mean_jump = results.get("mean_jump_contribution")
    jump_alpha = results.get("jump_alpha", 0.01)

    cont_persist = results.get("continuous_persistence_sum")
    jump_persist = results.get("jump_persistence_sum")
    r2 = results.get("R2")
    r2_adj = results.get("R2_adj")

    # Jump fraction + BNS clause
    if jump_frac is not None:
        try:
            jf = float(jump_frac)
            jumps_clause = (
                f"{n_jumps} of {n_raw} days ({jf * 100:.1f}%) "
                f"classified as jumps (BNS ratio test at α = "
                f"{float(jump_alpha):.2f})"
            )
        except Exception:
            jumps_clause = "jump fraction unavailable"
    else:
        jumps_clause = "jump fraction unavailable"

    # Mean jump contribution clause
    contrib_clause = ""
    if mean_jump is not None:
        try:
            mj = float(mean_jump)
            contrib_clause = (
                f"jump days contribute "
                f"{mj * 100:.0f}% of total realized variance "
                f"on average"
            )
        except Exception:
            pass

    # Central ABD 2007 persistence contrast — the signature Tier 1
    # phrase that distinguishes HAR-CJ from HAR-RV's Tier 1.
    persist_clause = ""
    if cont_persist is not None and jump_persist is not None:
        try:
            cp = float(cont_persist)
            jp = float(jump_persist)
            # "strongly dominates" when |cp| > 2*|jp|; else
            # "dominates" when cp > jp; else "competes with"
            if abs(cp) > 2 * abs(jp):
                verb = "strongly dominates"
            elif cp > jp:
                verb = "dominates"
            else:
                verb = "competes with"
            # ABD 2007 alignment: their central finding is
            # cont-persistence >> jump-persistence, with jumps
            # often statistically indistinguishable from zero.
            alignment = (
                "consistent with Andersen-Bollerslev-Diebold 2007 "
                "finding that jumps have near-zero persistence "
                "while continuous volatility is highly persistent"
                if cp > jp and abs(cp) > 2 * abs(jp)
                else "in contrast to the typical Andersen-Bollerslev-"
                     "Diebold 2007 finding of near-zero jump "
                     "persistence; inspect jump identification "
                     "quality and series regime"
            )
            persist_clause = (
                f"Continuous persistence Σβ_c = "
                f"{FMT_COEF_SIGNED.format(cp)} {verb} jump "
                f"persistence Σβ_j = {FMT_COEF_SIGNED.format(jp)} — "
                f"{alignment}."
            )
        except Exception:
            pass

    # Forecaster-family baseline comparison (reused from HAR-RV
    # pattern via _forecast_common helpers)
    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get(
            "baseline_label", "rolling-22-period mean RV",
        ),
    )

    # Fit-quality clause
    fit_clause = ""
    if r2 is not None and r2_adj is not None:
        try:
            fit_clause = (
                f"Fit R² = {FMT_COEF_UNSIGNED.format(float(r2))} "
                f"(adjusted {FMT_COEF_UNSIGNED.format(float(r2_adj))}) "
                f"on {n} effective observations"
            )
        except Exception:
            fit_clause = ""

    # Assemble Tier 1
    contrib_suffix = f"; {contrib_clause}" if contrib_clause else ""
    return (
        f"HAR-CJ (Andersen-Bollerslev-Diebold 2007) decomposition "
        f"of realized volatility for "
        f"{format_series_reference(name)} over {horizon_phrase}. "
        f"{jumps_clause}{contrib_suffix}. {persist_clause} "
        f"{baseline_clause}; {fit_clause}."
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    daily = int(results.get("daily_lag", 1) or 1)
    weekly = int(results.get("weekly_lag", 5) or 5)
    monthly = int(results.get("monthly_lag", 22) or 22)
    model = str(results.get("model", "HAR-CJ"))
    use_log = bool(results.get("use_log", False))

    b0 = results.get("beta_0")
    bcd = results.get("beta_cd"); bcw = results.get("beta_cw"); bcm = results.get("beta_cm")
    bjd = results.get("beta_jd"); bjw = results.get("beta_jw"); bjm = results.get("beta_jm")
    cps = results.get("continuous_persistence_sum")
    jps = results.get("jump_persistence_sum")

    def _fmt(v):
        if v is None:
            return "n/a"
        try:
            return FMT_COEF_SIGNED.format(float(v))
        except Exception:
            return "n/a"

    coef_clause = (
        f"Coefficients: β₀ = {_fmt(b0)}, β_cd = {_fmt(bcd)}, "
        f"β_cw = {_fmt(bcw)}, β_cm = {_fmt(bcm)}, β_jd = {_fmt(bjd)}, "
        f"β_jw = {_fmt(bjw)}, β_jm = {_fmt(bjm)}."
    )

    persist_clause = ""
    if cps is not None and jps is not None:
        try:
            persist_clause = (
                f" Continuous persistence sum = "
                f"{FMT_COEF_UNSIGNED.format(float(cps))}; jump "
                f"persistence sum = {FMT_COEF_SIGNED.format(float(jps))}."
            )
        except Exception:
            pass

    aic = results.get("aic"); bic = results.get("bic")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "n/a"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "n/a"

    lb_p = results.get("ljung_box_lag10_pvalue")
    jb_p = results.get("jarque_bera_pvalue")
    lb_clause = ""
    if lb_p is not None:
        try:
            verdict = (
                "does-not-reject white-noise"
                if float(lb_p) >= 0.05
                else "rejects white-noise"
            )
            lb_clause = (
                f" Residual Ljung-Box at lag 10 {verdict} "
                f"(p = {FMT_P_VALUE.format(float(lb_p))})."
            )
        except Exception:
            pass
    jb_clause = ""
    if jb_p is not None:
        try:
            verdict = (
                "does-not-reject"
                if float(jb_p) >= 0.05
                else "rejects"
            )
            jb_clause = (
                f" Jarque-Bera {verdict} residual normality "
                f"(p = {FMT_P_VALUE.format(float(jb_p))})."
            )
        except Exception:
            pass

    # Jump detection methodology block
    M = results.get("M_sampling_frequency")
    jump_alpha = results.get("jump_alpha", 0.01)
    jump_thresh = results.get("jump_detection_threshold")
    bns_max = results.get("bns_test_statistic_max")
    tq_approx = bool(results.get("tq_approximated", False))
    jump_methodology = (
        f" Jump detection methodology: Barndorff-Nielsen-Shephard "
        f"ratio test at α = {float(jump_alpha):.2f} "
        f"(threshold = Φ⁻¹(1−α) ≈ "
        f"{FMT_COEF_UNSIGNED.format(float(jump_thresh)) if jump_thresh is not None else 'n/a'}). "
        f"z-statistic = (RV_t − BV_t) / √(θ · max(TQ_t, BV_t²) / M) "
        f"with θ = (π/2)² + π − 5 ≈ 0.609 and M = "
        f"{int(M) if M is not None else 'unspecified'}. "
        f"Classification: is_jump_t = (Z_t > threshold); "
        f"J_t = max(RV_t − BV_t, 0) on jump days else 0; "
        f"C_t = RV_t − J_t. Max observed Z over the sample = "
        f"{FMT_COEF_UNSIGNED.format(float(bns_max)) if bns_max is not None else 'n/a'}."
    )

    # TQ approximation conditional disclosure
    tq_clause = ""
    if tq_approx:
        tq_clause = (
            " Realized tripower quarticity (TQ) was not supplied "
            "and has been approximated as BV² — a jump-robust "
            "lower bound on the true integrated quarticity. This "
            "approximation affects jump-detection precision at the "
            "borderline; see Tier 3 D2 for remediation guidance."
        )

    # Input contract reminder
    input_clause = (
        " Input contract: series[0] = RV (required), series[1] = "
        "BV (required), series[2] = TQ (optional; BV² fallback). "
        "ctx.params['M'] required (intraday sampling frequency)."
    )

    # Scale note (inherit from HAR-RV)
    scale_clause = (
        " **Scale note:** Fit RMSE is on realized-variance scale, "
        "not on return scale — direct RMSE comparison with return-"
        "forecasting techniques such as ARIMA is not meaningful. "
        "**Annualization:** daily volatility × √252 ≈ 15.87 "
        "converts to annual-scale volatility; daily variance × 252 "
        "converts to annual-scale variance."
    )

    # OLS SE caveat (inherit from HAR-RV)
    se_clause = (
        " **Standard errors:** OLS under iid normal-residuals "
        "assumption (not HAC / Newey-West corrected); HAR-CJ "
        "residuals may exhibit heteroscedasticity and "
        "autocorrelation, so coefficient-level significance "
        "should be treated as indicative."
    )

    log_clause = (
        " Log-HAR-CJ form applied; note J (jump component) has "
        "many zero values on non-jump days, and log(J + ε) "
        "introduces large negative spikes that may distort OLS. "
        "Consider use_log=False on HAR-CJ unless the RV "
        "distribution is heavily right-skewed."
        if use_log else
        " Raw-scale HAR-CJ fit; use_log=True is available but "
        "often awkward on HAR-CJ because J=0 on most days."
    )

    # Refit suggestions
    followup = (
        " For a pure cascade fit (no jump decomposition), compare "
        "against HAR-RV. If jump fraction looks implausible "
        "(Tier 3 D1 fires), verify the upstream M parameter and "
        "BV computation against your intraday data."
    )

    return (
        f"HAR-CJ (Heterogeneous Autoregressive on continuous + "
        f"jump realized-variance components; Andersen-Bollerslev-"
        f"Diebold 2007) via OLS: y_t = β₀ + β_cd · C_{{t−1}} + "
        f"β_cw · avg_wk(C) + β_cm · avg_mo(C) + β_jd · J_{{t−1}} + "
        f"β_jw · avg_wk(J) + β_jm · avg_mo(J) + ε_t at lags "
        f"{daily} / {weekly} / {monthly}. {coef_clause}"
        f"{persist_clause} Fit AIC = {aic_str}, BIC = {bic_str} "
        f"on {n} effective observations.{lb_clause}{jb_clause}"
        f"{jump_methodology}{tq_clause}{input_clause}{scale_clause}"
        f"{se_clause}{log_clause}{followup}"
    )


# ---------------------------------------------------------------------
# Tier 3 triggers — Follow-up 3b D1–D4
# ---------------------------------------------------------------------


def _trigger_jump_fraction_unusual(results: dict) -> Optional[str]:
    """D1 — fires when jump_days_fraction < 0.5% OR > 20%.

    Lower bound is "half the nominal α = 0.01 rate" (Q7
    refinement); rate < 0.5% suggests M or α mis-set.
    Upper bound > 20% suggests microstructure-noise pollution
    or genuinely unusual regime.
    """
    frac = results.get("jump_days_fraction")
    if frac is None:
        return None
    try:
        v = float(frac)
    except Exception:
        return None
    if 0.005 <= v <= 0.20:
        return None
    alpha = float(results.get("jump_alpha", 0.01))
    M = results.get("M_sampling_frequency")
    if v < 0.005:
        return (
            f"Jump fraction {v * 100:.1f}% is lowly unusual — "
            f"lower than half the nominal α = {alpha:.2f} rate. "
            f"This suggests either M (intraday sampling frequency, "
            f"currently {M}) is mis-set, or the test's null "
            f"distribution is being rejected too conservatively. "
            f"Verify M matches your intraday return granularity. "
            f"HAR-CJ decomposition is unlikely to add value over "
            f"HAR-RV on this sample."
        )
    return (
        f"Jump fraction {v * 100:.1f}% is highly unusual — "
        f"materially higher than the expected jump rate for "
        f"typical equity returns (1–5%). This suggests either "
        f"microstructure noise was not filtered upstream (yielding "
        f"inflated RV − BV differences), M = {M} is mis-set, or "
        f"the market regime is genuinely unusual (crisis, flash "
        f"event). HAR-CJ decomposition may not be informative "
        f"in this state."
    )


def _trigger_tq_approximated(results: dict) -> Optional[str]:
    """D2 — fires when TQ was derived from BV² instead of supplied."""
    if not bool(results.get("tq_approximated", False)):
        return None
    return (
        f"Realized tripower quarticity (TQ) was not supplied and "
        f"has been approximated as BV². This approximation is "
        f"conservative (BV² is a jump-robust lower bound on the "
        f"true integrated quarticity) but affects jump-detection "
        f"precision: borderline z-statistics near the threshold "
        f"may flip between jump / non-jump classification under "
        f"the true TQ. For precision-critical applications, supply "
        f"TQ as a third input series computed from intraday data: "
        f"TQ_t = M · μ_{{4/3}}⁻³ · Σ |r_i|^{{4/3}} · "
        f"|r_{{i-1}}|^{{4/3}} · |r_{{i-2}}|^{{4/3}}."
    )


def _trigger_jump_persistence_negative(results: dict) -> Optional[str]:
    """D3 — fires when any β_j* is significantly negative (p < 0.05
    AND coefficient < 0). ABD 2007 predicted near-zero positive."""
    for beta_key, p_key in [
        ("beta_jd", "beta_jd_pvalue"),
        ("beta_jw", "beta_jw_pvalue"),
        ("beta_jm", "beta_jm_pvalue"),
    ]:
        b = results.get(beta_key)
        p = results.get(p_key)
        if b is None or p is None:
            continue
        try:
            bf = float(b)
            pf = float(p)
        except Exception:
            continue
        if bf < 0.0 and pf < 0.05:
            return (
                f"Jump persistence coefficient {beta_key} = "
                f"{FMT_COEF_SIGNED.format(bf)} is significantly "
                f"negative (p = {FMT_P_VALUE.format(pf)}). Andersen-"
                f"Bollerslev-Diebold 2007 predicted near-zero "
                f"positive; significantly negative is an anomaly. "
                f"Potential causes: (a) jump identification upstream "
                f"is too aggressive (inflated jump count includes "
                f"non-jump days); (b) sample contains mean-reverting "
                f"post-jump dynamics at this horizon; (c) regression "
                f"is capturing a structural-break effect. Inspect "
                f"individual identified jump days for plausibility."
            )
    return None


def _trigger_jump_explains_excess_variation(results: dict) -> Optional[str]:
    """D4 — fires when mean_jump_contribution > 0.50."""
    contrib = results.get("mean_jump_contribution")
    if contrib is None:
        return None
    try:
        v = float(contrib)
    except Exception:
        return None
    if v <= 0.50:
        return None
    return (
        f"Mean jump contribution {v * 100:.1f}% of realized "
        f"variance exceeds 50% — jumps explain more than half of "
        f"total RV on this sample. This is unusual for normal "
        f"market regimes. Potential causes: (a) BV is mis-estimated "
        f"upstream (RV − BV inflated by microstructure noise, "
        f"yielding false 'jump' labels); (b) sample contains an "
        f"extreme regime (crisis period, bubble burst); (c) intraday "
        f"data had insufficient resolution (small M) causing RV to "
        f"overstate jumps relative to BV. Verify BV computation and "
        f"the M parameter before interpreting HAR-CJ output."
    )


# Inherited family-level triggers (same pattern as HAR-RV)


def _trigger_rmse_exceeds_baseline(results: dict) -> Optional[str]:
    """Inherited from HAR-family pattern. Fires when fit RMSE
    exceeds rolling-22-period mean RV baseline."""
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None:
        return None
    try:
        if float(fit) < float(base):
            return None
    except Exception:
        return None
    label = str(results.get("baseline_label", "rolling-mean RV"))
    return (
        f"Fit RMSE {format_scale_aware(float(fit))} matches or "
        f"exceeds the {label} baseline's "
        f"{format_scale_aware(float(base))}. HAR-CJ does not beat "
        f"the simple rolling-mean volatility forecast on this "
        f"series — the jump / continuous decomposition may not "
        f"add predictive value over a trailing average. Consider "
        f"HAR-RV for a simpler cascade."
    )


def _trigger_low_r2(results: dict) -> Optional[str]:
    """Inherited from HAR-family pattern. Fires when R² < 0.30."""
    r2 = results.get("R2")
    if r2 is None:
        return None
    try:
        v = float(r2)
    except Exception:
        return None
    if v >= 0.30:
        return None
    return (
        f"HAR-CJ R² = {FMT_COEF_UNSIGNED.format(v)} is moderate-"
        f"low, suggesting the daily / weekly / monthly cascade on "
        f"C and J may not capture the full volatility dynamics of "
        f"this series. Consider: (a) verifying the jump-detection "
        f"setup (M, α, BV computation); (b) comparing against "
        f"HAR-RV for a simpler cascade; (c) extending lags beyond "
        f"22 for long-memory volatility."
    )


SPEC = InterpretationSpec(
    technique_id="har_cj",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # Follow-up 3b D1-D4
        _trigger_jump_fraction_unusual,
        _trigger_tq_approximated,
        _trigger_jump_persistence_negative,
        _trigger_jump_explains_excess_variation,
        # Inherited HAR-family triggers
        _trigger_rmse_exceeds_baseline,
        _trigger_low_r2,
    ),
    mode_aware=False,
)

register(SPEC)
