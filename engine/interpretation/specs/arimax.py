"""
InterpretationSpec for arimax (ARIMA with exogenous regressors).

Inherits the Prompt C2 forecaster Tier 1 template (horizon + fit RMSE vs
naive + forecast_end_value with trend_pct + order disclosure). Tier 2
adds exogenous-coefficient disclosure plus the Decision D13 exog-carry
convention — naive baseline uses last-value-carried-forward for both
the endogenous series and the exogenous regressors, making the RMSE
comparison apples-to-apples on identical exogenous paths.

Results-dict keys consumed:

    series_name            : str
    n_obs                  : int
    horizon                : int
    order                  : (p, d, q) tuple
    fit_rmse               : float
    baseline_rmse          : float
    baseline_label         : str
    last_observed_value    : float
    forecast_end_value     : float
    series_mean            : float
    series_std             : float
    aic / bic              : float
    ljung_box_lag10_pvalue : float
    jarque_bera_pvalue     : float
    converged              : bool
    exog_count             : int
    exog_names             : list[str]
    exog_coefs             : list[dict{"name","coef","p_value"}]
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


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    order = _order_str(results.get("order"))
    exog_count = int(results.get("exog_count", 0) or 0)
    exog_names = list(results.get("exog_names") or [])
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
    exog_phrase = f"{exog_count} exogenous regressor{'s' if exog_count != 1 else ''}"
    if exog_names:
        exog_phrase += f" ({', '.join(exog_names)})"
    return (
        f"ARIMAX{order} forecast for {format_series_reference(name)} "
        f"({n} observations) with {exog_phrase} over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. "
        f"Manual-order specification with exogenous regressors; "
        f"exogenous coefficient significance disclosed in Tier 2."
    )


def _tier2(results: dict) -> str:
    order = _order_str(results.get("order"))
    order_tuple = results.get("order") or (0, 0, 0)
    try:
        p, d, q = int(order_tuple[0]), int(order_tuple[1]), int(order_tuple[2])
    except Exception:
        p = d = q = 0
    n = int(results.get("n_obs", 0))
    aic = results.get("aic")
    bic = results.get("bic")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"

    # Exogenous coefficient disclosure
    exog_coefs = list(results.get("exog_coefs") or [])
    exog_clauses = []
    for c in exog_coefs:
        try:
            name = str(c.get("name", "(unnamed)"))
            coef = float(c.get("coef", 0.0))
            p_val = c.get("p_value")
            if p_val is None:
                exog_clauses.append(
                    f"{name} coefficient {FMT_COEF_SIGNED.format(coef)} "
                    f"(p-value unavailable)"
                )
            else:
                p_val_f = float(p_val)
                if p_val_f < 0.05:
                    verdict = "significant at 5%"
                elif p_val_f < 0.10:
                    verdict = "marginal at 10%"
                else:
                    verdict = "not significant"
                exog_clauses.append(
                    f"{name} coefficient {FMT_COEF_SIGNED.format(coef)} "
                    f"(p={FMT_P_VALUE.format(p_val_f)}, {verdict})"
                )
        except Exception:
            continue
    exog_disclosure = (
        ("Exogenous coefficient significance: " + "; ".join(exog_clauses) + ".")
        if exog_clauses else "No exogenous coefficients reported."
    )

    converged = results.get("converged")
    convergence_clause = ""
    if converged is False:
        convergence_clause = (
            " Maximum-likelihood optimization did not fully converge on this run; "
            "coefficient standard errors and p-values are approximate."
        )

    diff_clause = (
        "One level of differencing applied."
        if d == 1 else
        (f"{d} levels of differencing applied."
         if d > 0 else "No differencing (d=0).")
    )

    # Decision D13 — exog-carry-forward convention disclosure
    carry_clause = (
        " Naive baseline uses last-value-carried-forward for both the "
        "endogenous series and exogenous regressors, making the RMSE "
        "comparison apples-to-apples on identical exogenous paths."
    )

    return (
        f"Manual ARIMAX{order} — user-chosen (p={p}, d={d}, q={q}) with "
        f"exogenous regressors. {diff_clause} Fit AIC {aic_str}, BIC {bic_str} "
        f"on {n} observations. {exog_disclosure}{convergence_clause}"
        f"{carry_clause} Unlike auto_arima with exog, this run does not "
        f"search over alternative orders; the rationale for (p,d,q) is the user's."
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
        f"does not beat naive on this series; reconsider specification or "
        f"treat with caution."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None or float(jb_p) >= 0.05:
        return None
    return (
        f"Residual normality test rejects at the 5% level "
        f"(JB p={FMT_P_VALUE.format(float(jb_p))}); prediction "
        f"intervals assume Gaussian errors and may be mis-calibrated. "
        f"Consider bootstrapped intervals or a heavier-tailed specification."
    )


def _trigger_convergence_failure(results: dict) -> Optional[str]:
    converged = results.get("converged")
    if converged is None or converged is True:
        return None
    return (
        "Maximum-likelihood optimization did not fully converge on this run. "
        "Coefficient standard errors and p-values are approximate. Re-run with "
        "increased maxiter or simpler order if exact inference is needed."
    )


def _trigger_exog_all_insignificant(results: dict) -> Optional[str]:
    exog_coefs = list(results.get("exog_coefs") or [])
    if not exog_coefs:
        return None
    any_sig = False
    for c in exog_coefs:
        try:
            p_val = c.get("p_value")
            if p_val is not None and float(p_val) < 0.05:
                any_sig = True
                break
        except Exception:
            continue
    if any_sig:
        return None
    return (
        f"None of the {len(exog_coefs)} exogenous regressors reach the 5% "
        f"significance threshold. The ARIMA structure alone may suffice — "
        f"refit without exog and compare AIC before committing to this spec."
    )


SPEC = InterpretationSpec(
    technique_id="arimax",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_residuals_non_normal,
        _trigger_convergence_failure,
        _trigger_exog_all_insignificant,
    ),
    mode_aware=False,
)

register(SPEC)
