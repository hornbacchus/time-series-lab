"""
InterpretationSpec for arima (manual order).

Distinct from auto_arima: this spec covers the manual-order case where
the user supplies (p,d,q) explicitly. Tier 2 discloses the user's
order choice without validating it against alternatives (see auto_arima
spec for the IC-search path).
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
    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "last-value naive"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value", 0.0)),
        forecast_end_value=float(results.get("forecast_end_value", 0.0)),
        series_std=float(results.get("series_std", 0.0)),
        horizon=horizon,
    )
    return (
        f"ARIMA{order} forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. "
        f"Manual-order specification; if residual Ljung-Box rejects "
        f"white-noise, reconsider (p,d,q)."
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
    lb_p = results.get("ljung_box_lag10_pvalue")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"
    diff_clause = (
        f"One level of differencing applied; the fitted model describes the differenced series."
        if d == 1 else
        (f"{d} levels of differencing applied."
         if d > 0 else "No differencing (d=0).")
    )
    if lb_p is not None:
        if float(lb_p) >= 0.05:
            lb_verdict = "does-not-reject white-noise"
            adequacy = " — ARMA structure is adequate"
        else:
            lb_verdict = "rejects white-noise"
            adequacy = " — ARMA structure is inadequate"
        lb_clause = (
            f"Residual Ljung-Box at lag 10 {lb_verdict} "
            f"(p={FMT_P_VALUE.format(float(lb_p))}){adequacy}."
        )
    else:
        lb_clause = "Residual Ljung-Box diagnostic unavailable."
    # Revision 2: actionable framing on closing sentence.
    return (
        f"Manual ARIMA{order} — user-chosen (p={p}, d={d}, q={q}). "
        f"{diff_clause} Fit AIC {aic_str}, BIC {bic_str} on {n} observations. "
        f"{lb_clause} Unlike auto_arima, this run uses the user-specified "
        f"(p,d,q) without comparing alternatives; running auto_arima on the "
        f"same series would disclose whether neighboring orders produce "
        f"materially lower AIC."
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


def _trigger_residual_structure(results: dict) -> Optional[str]:
    lb_p = results.get("ljung_box_lag10_pvalue")
    if lb_p is None or float(lb_p) >= 0.05:
        return None
    return (
        f"Residual Ljung-Box rejects white-noise at the 5% level "
        f"(p={FMT_P_VALUE.format(float(lb_p))}); the ARMA structure is "
        f"inadequate. Review the order or consider seasonal terms."
    )


def _trigger_pathological_order(results: dict) -> Optional[str]:
    order = results.get("order")
    n = int(results.get("n_obs", 0))
    if not order or n <= 0:
        return None
    try:
        p, d, q = int(order[0]), int(order[1]), int(order[2])
    except Exception:
        return None
    pq = p + q
    sqrtn = n ** 0.5
    if pq <= sqrtn:
        return None
    return (
        f"Order (p+q)={pq} exceeds sqrt(n_obs)={sqrtn:.0f}; the "
        f"specification may be overfitted relative to sample size."
    )


def _trigger_differencing_overkill(results: dict) -> Optional[str]:
    order = results.get("order")
    if not order:
        return None
    try:
        d = int(order[1])
    except Exception:
        return None
    if d < 2:
        return None
    return (
        f"Two or more differencing rounds applied; verify non-stationarity "
        f"of the once-differenced series before accepting d≥2."
    )


SPEC = InterpretationSpec(
    technique_id="arima",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_residual_structure,
        _trigger_pathological_order,
        _trigger_differencing_overkill,
    ),
    mode_aware=False,
)

register(SPEC)
