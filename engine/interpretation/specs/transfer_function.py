"""
InterpretationSpec for transfer_function (distributed lag + AR noise).

NEW Tier 1 shape — input-output dynamic regression. Cites gain (long-run
multiplier) with adjective band (Decision D12), peak_lag with careful
phrasing (Decision D11 — "dominant response at lag N", not conflated
with formal Box-Jenkins delay `b`), and the order specification.

Decision D10: Tier 2 always-on order-misspecification honest disclosure —
transfer-function model-order misspecification is the dominant failure
mode; residual Ljung-Box is the primary specification check.

Decision D12 — gain adjective bands (in-spec, first use; promote on
second distinct consumer per the primitives future-promotion convention):

    |gain| < 0.1      -> "negligible"
    0.1 <= |gain| < 0.5 -> "moderate"
    0.5 <= |gain| < 1.0 -> "strong"
    |gain| >= 1.0      -> "amplifying"

Results-dict keys consumed:

    y_series / x_series
    max_lag / ar_order / polynomial
    r_squared / adj_r_squared / rmse / aic / bic
    long_run_multiplier / peak_lag / peak_lag_weight
    n_effective / n_observations
    jarque_bera_pvalue / durbin_watson / ljung_box_lag10_pvalue
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_COEF_UNSIGNED,
    FMT_COEF_SIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _gain_band(gain: float) -> str:
    # TODO: promote to shared forecaster primitive on second consumer
    # per the primitives.py future-promotion convention.
    v = abs(float(gain))
    if v < 0.1:
        return "negligible"
    if v < 0.5:
        return "moderate"
    if v < 1.0:
        return "strong"
    return "amplifying"


def _tier1(results: dict) -> str:
    y = str(results.get("y_series", "output"))
    x = str(results.get("x_series", "input"))
    n = int(results.get("n_observations") or results.get("n_effective", 0))
    max_lag = int(results.get("max_lag", 0) or 0)
    ar_order = int(results.get("ar_order", 0) or 0)
    poly = str(results.get("polynomial", "unrestricted"))
    gain = results.get("long_run_multiplier")
    peak_lag = results.get("peak_lag")
    r2 = results.get("r_squared")
    n_eff = int(results.get("n_effective", 0) or 0)
    lb_p = results.get("ljung_box_lag10_pvalue")

    try:
        gain_f = float(gain) if gain is not None else None
    except Exception:
        gain_f = None

    if gain_f is not None:
        gain_str = format_scale_aware(gain_f)
        gain_band = _gain_band(gain_f)
        gain_clause = (
            f"Long-run gain {gain_str} ({gain_band})"
            + (" — the net-cumulative effect is near zero across the "
               f"{max_lag}-period response window" if gain_band == "negligible"
               else "")
            + "."
        )
    else:
        gain_clause = "Long-run gain unavailable."

    # Decision D11 — "dominant response at lag N" phrasing; NOT conflated
    # with Box-Jenkins delay b.
    if peak_lag is not None:
        try:
            pl = int(peak_lag)
            pk_weight = results.get("peak_lag_weight")
            if pk_weight is not None:
                peak_clause = (
                    f" Dominant response at lag {pl} "
                    f"(weight {FMT_COEF_SIGNED.format(float(pk_weight))})."
                )
            else:
                peak_clause = f" Dominant response at lag {pl}."
        except Exception:
            peak_clause = ""
    else:
        peak_clause = ""

    r2_clause = ""
    if r2 is not None:
        try:
            r2_clause = (
                f" R² = {FMT_COEF_UNSIGNED.format(float(r2))} on {n_eff} "
                f"effective observations."
            )
        except Exception:
            r2_clause = ""

    lb_clause = ""
    if lb_p is not None:
        try:
            lb_f = float(lb_p)
            if lb_f < 0.05:
                lb_clause = (
                    f" Residual Ljung-Box rejects white-noise "
                    f"(p={FMT_P_VALUE.format(lb_f)}) — revisit model orders "
                    f"before interpreting gain or delay."
                )
            else:
                lb_clause = (
                    f" Residual Ljung-Box does-not-reject "
                    f"(p={FMT_P_VALUE.format(lb_f)})."
                )
        except Exception:
            pass

    return (
        f"Transfer function of {format_series_reference(y)} on "
        f"{format_series_reference(x)} ({n} observations) with max_lag="
        f"{max_lag} and ar_order={ar_order} via {poly} OLS. "
        f"{gain_clause}{peak_clause}{r2_clause}{lb_clause}"
    )


def _tier2(results: dict) -> str:
    n_eff = int(results.get("n_effective", 0) or 0)
    r2 = results.get("r_squared")
    adj_r2 = results.get("adj_r_squared")
    rmse = results.get("rmse")
    aic = results.get("aic")
    bic = results.get("bic")
    dw = results.get("durbin_watson")
    jb_p = results.get("jarque_bera_pvalue")
    lb_p = results.get("ljung_box_lag10_pvalue")
    max_lag = int(results.get("max_lag", 0) or 0)
    ar_order = int(results.get("ar_order", 0) or 0)

    r2_s = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
    adj_s = FMT_COEF_UNSIGNED.format(float(adj_r2)) if adj_r2 is not None else "n/a"
    rmse_s = format_scale_aware(float(rmse)) if rmse is not None else "n/a"
    aic_s = format_scale_aware(float(aic)) if aic is not None else "n/a"
    bic_s = format_scale_aware(float(bic)) if bic is not None else "n/a"

    dw_clause = ""
    if dw is not None:
        try:
            dw_f = float(dw)
            if abs(dw_f - 2.0) <= 0.3:
                dw_clause = (
                    f" Durbin-Watson {dw_f:.2f} indicates no first-order "
                    f"residual autocorrelation."
                )
            elif dw_f < 1.5:
                dw_clause = (
                    f" Durbin-Watson {dw_f:.2f} indicates positive residual "
                    f"autocorrelation."
                )
            else:
                dw_clause = (
                    f" Durbin-Watson {dw_f:.2f} indicates negative residual "
                    f"autocorrelation."
                )
        except Exception:
            pass

    jb_clause = ""
    if jb_p is not None:
        try:
            if float(jb_p) < 0.05:
                jb_clause = (
                    f" Residual Jarque-Bera rejects normality "
                    f"(p={FMT_P_VALUE.format(float(jb_p))})."
                )
            else:
                jb_clause = (
                    f" Residual Jarque-Bera does-not-reject normality "
                    f"(p={FMT_P_VALUE.format(float(jb_p))})."
                )
        except Exception:
            pass

    if lb_p is not None:
        try:
            lb_clause = (
                f" Residual Ljung-Box at lag 10 "
                f"(p={FMT_P_VALUE.format(float(lb_p))})."
            )
        except Exception:
            lb_clause = ""
    else:
        lb_clause = " Residual Ljung-Box not computed."

    # Decision D10 — always-fire order-misspecification caveat
    order_caveat = (
        f" Model orders for the distributed-lag polynomial (max_lag={max_lag}) "
        f"and AR noise (ar_order={ar_order}) are user-specified; "
        f"misspecification is the dominant failure mode for transfer "
        f"functions. If residual Ljung-Box rejects white-noise, revisit "
        f"(max_lag, ar_order) before interpreting gain or delay coefficients. "
        f"Long-run multiplier is computed as the sum of distributed-lag "
        f"weights (cumulative gain); it reflects the net steady-state "
        f"effect of a unit impulse in the input."
    )

    # Exogeneity honest-disclosure
    exog_sentence = (
        f" The input series is assumed to be weakly exogenous with respect "
        f"to the output; feedback from output to input (via simultaneity or "
        f"reaction-function dynamics) is NOT modeled here and would bias "
        f"gain estimates."
    )

    return (
        f"Box-Jenkins-style transfer function: Y_t = c + Σ ω_k · X_{{t-k}} + "
        f"Σ φ_j · Y_{{t-j}} + ε_t. Fit via ordinary least squares on {n_eff} "
        f"effective observations. R² {r2_s}, adjusted R² {adj_s}, RMSE "
        f"{rmse_s}, AIC {aic_s}, BIC {bic_s}.{dw_clause}{jb_clause}{lb_clause}"
        f"{order_caveat}{exog_sentence}"
    )


def _trigger_ljung_box_rejects(results: dict) -> Optional[str]:
    lb_p = results.get("ljung_box_lag10_pvalue")
    if lb_p is None:
        return None
    try:
        v = float(lb_p)
    except Exception:
        return None
    if v >= 0.05:
        return None
    return (
        f"Residual Ljung-Box at lag 10 rejects white-noise "
        f"(p={FMT_P_VALUE.format(v)}). Model orders (max_lag, ar_order) are "
        f"likely misspecified; gain and delay coefficients are not "
        f"interpretable until this test passes. Revisit the order selection "
        f"before using the fit for inference."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None:
        return None
    try:
        v = float(jb_p)
    except Exception:
        return None
    if v >= 0.05:
        return None
    return (
        f"Residual Jarque-Bera rejects normality at the 5% level "
        f"(p={FMT_P_VALUE.format(v)}); prediction intervals assume Gaussian "
        f"errors and may be mis-calibrated. Consider bootstrapped intervals "
        f"or a heavier-tailed noise specification."
    )


def _trigger_negligible_gain_low_r2(results: dict) -> Optional[str]:
    gain = results.get("long_run_multiplier")
    r2 = results.get("r_squared")
    if gain is None or r2 is None:
        return None
    try:
        g = abs(float(gain))
        r = float(r2)
    except Exception:
        return None
    if g >= 0.1 or r >= 0.2:
        return None
    return (
        f"Long-run gain is negligible (|gain|={g:.3f} < 0.1) and model R² is "
        f"low ({r:.3f} < 0.2); the input series explains little of the "
        f"output's variance and its cumulative net effect is near zero. "
        f"Either the true relationship is weak, or the order specification "
        f"is capturing noise rather than signal — revisit (max_lag, ar_order) "
        f"and check residual Ljung-Box."
    )


SPEC = InterpretationSpec(
    technique_id="transfer_function",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_ljung_box_rejects,
        _trigger_residuals_non_normal,
        _trigger_negligible_gain_low_r2,
    ),
    mode_aware=False,
)

register(SPEC)
