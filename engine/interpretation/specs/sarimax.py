"""
InterpretationSpec for sarimax (seasonal ARIMA with optional exogenous
regressors).

Inherits the Prompt C2 forecaster Tier 1 template. Tier 2 adds the
seasonal specification disclosure and — when exog is present — the
exog-carry-forward convention from Decision D13.

Decision D14: overparameterization trigger uses composite threshold
(p + q + P + Q > 6) AND (p + q + P + Q > 0.1 × n_obs) to avoid firing
on short but legitimately seasonal specifications.

Results-dict keys consumed:

    series_name            : str
    n_obs                  : int
    horizon                : int
    order                  : (p, d, q) tuple
    seasonal_order         : (P, D, Q, m) tuple
    fit_rmse / baseline_rmse / baseline_label / last_observed_value
    forecast_end_value / series_mean / series_std
    aic / bic
    ljung_box_lag10_pvalue / jarque_bera_pvalue
    converged
    exog_count / exog_names / exog_coefs
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
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)

PRESET_GATED_KEYS = ()


def _order_str(order) -> str:
    if not order:
        return "(p,d,q)"
    try:
        p, d, q = int(order[0]), int(order[1]), int(order[2])
        return f"({p},{d},{q})"
    except Exception:
        return str(order)


def _seasonal_order_str(seasonal) -> str:
    if not seasonal:
        return "(0,0,0)[1]"
    try:
        P, D, Q, m = int(seasonal[0]), int(seasonal[1]), int(seasonal[2]), int(seasonal[3])
        return f"({P},{D},{Q})[{m}]"
    except Exception:
        return str(seasonal)


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    order = _order_str(results.get("order"))
    seasonal = _seasonal_order_str(results.get("seasonal_order"))
    exog_count = int(results.get("exog_count", 0) or 0)
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
    if exog_count > 0:
        exog_names = list(results.get("exog_names") or [])
        exog_phrase = f" with {exog_count} exogenous regressor{'s' if exog_count != 1 else ''}"
        if exog_names:
            exog_phrase += f" ({', '.join(exog_names)})"
        exog_phrase += ""
        closing = "Seasonal + exog disclosure in Tier 2"
    else:
        exog_phrase = ""
        closing = (
            "Seasonal specification absorbs the periodic cycle; no exogenous regressors"
        )
    return (
        f"SARIMAX{order}{seasonal} forecast for {format_series_reference(name)} "
        f"({n} observations){exog_phrase} over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. {closing}."
    )


def _tier2(results: dict) -> str:
    order = _order_str(results.get("order"))
    seasonal = _seasonal_order_str(results.get("seasonal_order"))
    order_tuple = results.get("order") or (0, 0, 0)
    seasonal_tuple = results.get("seasonal_order") or (0, 0, 0, 1)
    try:
        p, d, q = int(order_tuple[0]), int(order_tuple[1]), int(order_tuple[2])
    except Exception:
        p = d = q = 0
    try:
        P, D, Q, m = (int(seasonal_tuple[0]), int(seasonal_tuple[1]),
                      int(seasonal_tuple[2]), int(seasonal_tuple[3]))
    except Exception:
        P = D = Q = 0
        m = 1
    n = int(results.get("n_obs", 0))
    aic = results.get("aic")
    bic = results.get("bic")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"

    lb_p = results.get("ljung_box_lag10_pvalue")
    if lb_p is not None:
        if float(lb_p) >= 0.05:
            lb_clause = (
                f"Residual Ljung-Box at lag 10 does-not-reject white-noise "
                f"(p={FMT_P_VALUE.format(float(lb_p))}) — seasonal ARMA structure adequate."
            )
        else:
            lb_clause = (
                f"Residual Ljung-Box at lag 10 rejects white-noise "
                f"(p={FMT_P_VALUE.format(float(lb_p))}); consider revising order."
            )
    else:
        lb_clause = "Residual Ljung-Box diagnostic unavailable."

    # Exog disclosure
    exog_coefs = list(results.get("exog_coefs") or [])
    if exog_coefs:
        exog_clauses = []
        for c in exog_coefs:
            try:
                name_c = str(c.get("name", "(unnamed)"))
                coef = float(c.get("coef", 0.0))
                p_val = c.get("p_value")
                if p_val is None:
                    exog_clauses.append(
                        f"{name_c} {FMT_COEF_SIGNED.format(coef)}"
                    )
                else:
                    exog_clauses.append(
                        f"{name_c} {FMT_COEF_SIGNED.format(coef)} "
                        f"(p={FMT_P_VALUE.format(float(p_val))})"
                    )
            except Exception:
                continue
        exog_sent = (
            " Exogenous regressors: " + "; ".join(exog_clauses) +
            ". Naive baseline uses last-value-carried-forward for both the "
            "endogenous series and exogenous regressors, making the RMSE "
            "comparison apples-to-apples on identical exogenous paths."
        )
    else:
        exog_sent = " No exogenous regressors in this run."

    diff_sent = ""
    if d > 0 or D > 0:
        parts = []
        if d > 0:
            parts.append(f"{d} non-seasonal differencing round{'s' if d != 1 else ''}")
        if D > 0:
            parts.append(f"{D} seasonal differencing round{'s' if D != 1 else ''} at period {m}")
        diff_sent = " " + (" and ".join(parts)).capitalize() + "."

    return (
        f"SARIMAX{order}{seasonal} — user-chosen (p={p}, d={d}, q={q}) "
        f"non-seasonal orders with (P={P}, D={D}, Q={Q}) seasonal orders "
        f"at period m={m}.{diff_sent} Fit AIC {aic_str}, BIC {bic_str} on "
        f"{n} observations. {lb_clause}{exog_sent} For forecasts: seasonal "
        f"ARMA assumes stable seasonal pattern; consider MSTL or STL + "
        f"ARIMA hybrid if seasonality evolves over the sample."
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
        f"does not beat naive on this series; reconsider specification."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None or float(jb_p) >= 0.05:
        return None
    return (
        f"Residual normality test rejects at the 5% level "
        f"(JB p={FMT_P_VALUE.format(float(jb_p))}); prediction intervals "
        f"assume Gaussian errors and may be mis-calibrated."
    )


def _trigger_convergence_failure(results: dict) -> Optional[str]:
    converged = results.get("converged")
    if converged is None or converged is True:
        return None
    return (
        "Maximum-likelihood optimization did not fully converge on this run. "
        "Coefficient standard errors and p-values are approximate. Re-run "
        "with increased maxiter or a simpler seasonal order if exact "
        "inference is needed."
    )


def _trigger_overparameterization(results: dict) -> Optional[str]:
    """D14 composite threshold: p + q + P + Q > 6 AND > 0.1 × n_obs.

    Avoids spurious firing on short but legitimately seasonal series
    where the absolute order is modest relative to typical seasonal
    specifications. TODO: promote to a shared forecaster primitive
    on the second consumer per the primitives.py future-promotion
    convention.
    """
    order = results.get("order") or (0, 0, 0)
    seasonal = results.get("seasonal_order") or (0, 0, 0, 1)
    try:
        p, q = int(order[0]), int(order[2])
        P, Q = int(seasonal[0]), int(seasonal[2])
    except Exception:
        return None
    total = p + q + P + Q
    n = int(results.get("n_obs", 0))
    if total <= 6:
        return None
    if n <= 0 or total <= 0.1 * n:
        return None
    return (
        f"Combined ARMA+SARMA order (p+q+P+Q={total}) is high and exceeds "
        f"10% of the sample size (n={n}). The model may be overparameterized; "
        f"test whether a simpler specification (e.g. the airline model "
        f"(0,1,1)(0,1,1)[m]) fits comparably via AIC/BIC."
    )


SPEC = InterpretationSpec(
    technique_id="sarimax",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_residuals_non_normal,
        _trigger_convergence_failure,
        _trigger_overparameterization,
    ),
    mode_aware=False,
)

register(SPEC)
