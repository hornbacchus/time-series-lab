"""
InterpretationSpec for har_rv (Heterogeneous Autoregressive on
Realized Volatility — Corsi 2009).

Inherits the Prompt C2 forecaster Tier 1 template (RMSE + baseline
comparison + horizon-trend) with a volatility-vs-return unit
distinction per Decision D3 (refined). Tier 1 uses "realized
volatility" noun phrase to anchor scale; Tier 2 adds explicit scale-
note plus Convention B annualization commentary (×√252).

Decision D2: rolling-22-period mean RV as naive baseline (monthly
window matching Corsi's monthly lag).
Decision D9: annualization note in Tier 2 prose (no wrapper change).
Decision D19: low-R² Tier 3 trigger at R² < 0.30 with actionable
extensions (log-HAR, longer lags, HAR-CJ jumps-aware).

Results-dict keys consumed:

    series_name / model (HAR-RV or log-HAR-RV)
    daily_lag / weekly_lag / monthly_lag / h_ahead / use_log
    beta_0 / beta_d / beta_w / beta_m / persistence_sum
    R2 / R2_adj / aic / bic
    fit_rmse / baseline_rmse / baseline_label
    forecast_end_value / last_observed_value / series_mean / series_std
    ljung_box_lag10_pvalue / jarque_bera_pvalue
    n_obs
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


def _dominant_component(beta_d, beta_w, beta_m) -> str:
    pairs = [("daily", beta_d), ("weekly", beta_w), ("monthly", beta_m)]
    try:
        pairs.sort(key=lambda p: abs(float(p[1])), reverse=True)
        return pairs[0][0]
    except Exception:
        return "weekly"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the RV series"))
    n = int(results.get("n_obs", 0))
    h = int(results.get("h_ahead", 1) or 1)
    daily = int(results.get("daily_lag", 1) or 1)
    weekly = int(results.get("weekly_lag", 5) or 5)
    monthly = int(results.get("monthly_lag", 22) or 22)

    bd = results.get("beta_d")
    bw = results.get("beta_w")
    bm = results.get("beta_m")
    r2 = results.get("R2")
    r2_adj = results.get("R2_adj")
    dom = _dominant_component(bd, bw, bm) if bd is not None else "weekly"

    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
    r2_adj_str = FMT_COEF_UNSIGNED.format(float(r2_adj)) if r2_adj is not None else "n/a"
    bd_str = FMT_COEF_SIGNED.format(float(bd)) if bd is not None else "n/a"
    bw_str = FMT_COEF_SIGNED.format(float(bw)) if bw is not None else "n/a"
    bm_str = FMT_COEF_SIGNED.format(float(bm)) if bm is not None else "n/a"

    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "rolling-22-period mean RV"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value") or 0.0),
        forecast_end_value=float(results.get("forecast_end_value") or 0.0),
        series_std=float(results.get("series_std") or 0.0),
        series_mean=results.get("series_mean"),
        horizon=h,
    )

    # Period phrasing (singular/plural for h=1 vs h>1).
    horizon_phrase = f"{h} period" if h == 1 else f"{h} periods"

    # Dominant-component color sentence.
    dom_str = {
        "daily": f"daily (β_d = {bd_str})",
        "weekly": f"weekly (β_w = {bw_str})",
        "monthly": f"monthly (β_m = {bm_str})",
    }.get(dom, f"weekly (β_w = {bw_str})")

    return (
        f"HAR-RV forecast of realized volatility for "
        f"{format_series_reference(name)} over {horizon_phrase}. "
        f"Heterogeneous AR model with daily, weekly, and monthly "
        f"components (Corsi 2009 default lag structure: "
        f"{daily}/{weekly}/{monthly}). {baseline_clause}; "
        f"{trend_clause}. Fit R² = {r2_str} (adjusted {r2_adj_str}) "
        f"on {n} effective observations; the {dom_str} component "
        f"dominates the response."
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    daily = int(results.get("daily_lag", 1) or 1)
    weekly = int(results.get("weekly_lag", 5) or 5)
    monthly = int(results.get("monthly_lag", 22) or 22)
    model = str(results.get("model", "HAR-RV"))
    use_log = bool(results.get("use_log", False))

    b0 = results.get("beta_0")
    bd = results.get("beta_d")
    bw = results.get("beta_w")
    bm = results.get("beta_m")
    psum = results.get("persistence_sum")
    b0_str = FMT_COEF_SIGNED.format(float(b0)) if b0 is not None else "n/a"
    bd_str = FMT_COEF_SIGNED.format(float(bd)) if bd is not None else "n/a"
    bw_str = FMT_COEF_SIGNED.format(float(bw)) if bw is not None else "n/a"
    bm_str = FMT_COEF_SIGNED.format(float(bm)) if bm is not None else "n/a"
    psum_str = FMT_COEF_UNSIGNED.format(float(psum)) if psum is not None else "n/a"

    aic = results.get("aic")
    bic = results.get("bic")
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

    log_clause = (
        " Log-HAR form fits the log-RV distribution (reduces "
        "right-skewness)."
        if use_log
        else " Raw-scale HAR-RV fit; consider log-HAR (use_log=True) "
             "if RV is heavily right-skewed."
    )

    return (
        f"Heterogeneous Autoregressive on Realized Variance ({model}) "
        f"via OLS with daily / weekly / monthly component regressors "
        f"at lags {daily} / {weekly} / {monthly} (Corsi 2009). "
        f"Coefficients: β₀ = {b0_str}, β_d = {bd_str}, β_w = {bw_str}, "
        f"β_m = {bm_str}; persistence sum β_d + β_w + β_m = {psum_str} "
        f"(stationary when below 1). Fit AIC = {aic_str}, "
        f"BIC = {bic_str} on {n} effective observations.{lb_clause}"
        f"{jb_clause} **Scale note:** Fit RMSE is on realized-variance "
        f"scale, not on return scale — direct RMSE comparison with "
        f"return-forecasting techniques such as ARIMA is not meaningful. "
        f"**Annualization:** daily volatility × √252 ≈ 15.87 converts "
        f"to annual-scale volatility; daily variance × 252 converts to "
        f"annual-scale variance. **Standard errors:** OLS under normal-"
        f"residuals assumption (not HAC/Newey-West corrected); HAR "
        f"residuals often exhibit heteroscedasticity and autocorrelation "
        f"on RV, so significance at the coefficient level should be "
        f"treated as indicative.{log_clause}"
    )


def _trigger_residual_structure(results: dict) -> Optional[str]:
    p = results.get("ljung_box_lag10_pvalue")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Residual Ljung-Box rejects the white-noise null "
        f"(p = {FMT_P_VALUE.format(float(p))}); HAR structure is "
        f"inadequate on this series. Consider (a) log-HAR form "
        f"(use_log=True) to stabilize the right-skewed RV distribution; "
        f"(b) adding lags beyond the monthly (22) horizon for long-"
        f"memory volatility dynamics; (c) a HAR-CJ variant if "
        f"identifiable price jumps contribute to RV."
    )


def _trigger_log_har_recommended(results: dict) -> Optional[str]:
    if bool(results.get("use_log", False)):
        return None
    p = results.get("jarque_bera_pvalue")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Residual Jarque-Bera rejects normality "
        f"(p = {FMT_P_VALUE.format(float(p))}); raw-scale HAR-RV is "
        f"sensitive to right-skewness in realized variance. Consider "
        f"refitting with use_log=True to stabilize the residual "
        f"distribution."
    )


def _trigger_rmse_exceeds_baseline(results: dict) -> Optional[str]:
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
        f"Fit RMSE {format_scale_aware(float(fit))} matches or exceeds "
        f"the {label} baseline's {format_scale_aware(float(base))}. "
        f"HAR-RV does not beat the simple rolling-mean volatility "
        f"forecast on this series — the lag structure may not add "
        f"predictive value over a trailing average."
    )


def _trigger_low_r2(results: dict) -> Optional[str]:
    """D19 — R² < 0.30 triggers the explanation-weak caveat with
    three actionable extensions."""
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
        f"HAR-RV R² = {FMT_COEF_UNSIGNED.format(v)} is moderate-low, "
        f"suggesting the daily / weekly / monthly lag structure may not "
        f"capture the full volatility dynamics of this series. "
        f"Consider: (a) log-HAR form (use_log=True) if RV distribution "
        f"is right-skewed; (b) adding lags beyond 22 for long-memory "
        f"volatility; (c) jumps-aware variants like HAR-CJ if the "
        f"series contains identifiable jumps."
    )


SPEC = InterpretationSpec(
    technique_id="har_rv",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_residual_structure,
        _trigger_log_har_recommended,
        _trigger_rmse_exceeds_baseline,
        _trigger_low_r2,
    ),
    mode_aware=False,
)

register(SPEC)
