"""
InterpretationSpec for auto_arima (IC-search ARIMA).

Distinct from arima: this spec covers pmdarima's stepwise (or
exhaustive) IC-minimization search. Tier 2 discloses the search
machinery explicitly — which IC, how many specifications, what
bounds — per §4.4 honest disclosure.
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


def _order_str_with_seasonal(order, seasonal_order, m=None) -> str:
    try:
        p, d, q = int(order[0]), int(order[1]), int(order[2])
        base = f"({p},{d},{q})"
        if seasonal_order and len(seasonal_order) >= 3:
            P, D, Q = int(seasonal_order[0]), int(seasonal_order[1]), int(seasonal_order[2])
            m_val = int(seasonal_order[3]) if len(seasonal_order) >= 4 else (int(m) if m else 1)
            if (P, D, Q) != (0, 0, 0) or m_val > 1:
                return f"{base}({P},{D},{Q})[{m_val}]"
        return base
    except Exception:
        return str(order)


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    order_str = _order_str_with_seasonal(
        results.get("order"), results.get("seasonal_order"),
        results.get("seasonal_period_m"),
    )
    n_cand = results.get("n_candidates_searched")
    stepwise = bool(results.get("stepwise", True))
    search_mode = "stepwise algorithm" if stepwise else "exhaustive grid search"
    # Stepwise candidate count is a lower-bound heuristic based on the
    # search-bound sums — pmdarima does not expose the exact count
    # without trace=True. Render as "at least N" for honesty.
    if n_cand:
        if stepwise:
            n_cand_str = f"at least {int(n_cand)} ARIMA specifications"
        else:
            n_cand_str = f"{int(n_cand)} ARIMA specifications"
    else:
        n_cand_str = "the configured search scope"
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
    ic = str(results.get("ic", "aic")).upper()
    return (
        f"Auto-ARIMA forecast for {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. "
        f"{baseline_clause}; {trend_clause}. "
        f"{ic}-minimized order {order_str} selected by searching "
        f"{n_cand_str} via pmdarima's {search_mode}."
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    order_str = _order_str_with_seasonal(
        results.get("order"), results.get("seasonal_order"),
        results.get("seasonal_period_m"),
    )
    ic = str(results.get("ic", "aic")).upper()
    aic = results.get("aic")
    bic = results.get("bic")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"
    stepwise = bool(results.get("stepwise", True))
    search_mode = "stepwise search algorithm" if stepwise else "exhaustive grid search"
    n_cand = results.get("n_candidates_searched")
    if n_cand:
        n_cand_str = (
            f"at least {int(n_cand)} specifications"
            if stepwise else f"{int(n_cand)} specifications"
        )
    else:
        n_cand_str = "the search scope"
    max_p = results.get("max_p")
    max_q = results.get("max_q")
    max_d = results.get("max_d")
    seasonal = (results.get("seasonal_period_m") or 1) > 1
    m_val = results.get("seasonal_period_m", 1)
    freq = results.get("frequency", "")
    m_inferred = bool(results.get("m_inferred_from_freq", False))
    bounds_clause = (
        f"Search bounds: max_p={max_p}, max_q={max_q}, max_d={max_d}, "
        f"seasonal={str(seasonal)}, m={m_val}"
        + (f" (auto-inferred from frequency '{freq}')" if (seasonal and m_inferred) else "")
        + "."
    )
    # Revision 3: stepwise-tie caveat moved immediately after the
    # search-disclosure sentence.
    tie_clause = (
        " Stepwise ties are broken by the algorithm's traversal order and "
        "are not reproducible across pmdarima versions — runner-up "
        "specifications within 2 AIC units may be equally plausible."
        if stepwise else ""
    )
    lb_p = results.get("ljung_box_lag10_pvalue")
    if lb_p is not None:
        lb_verdict = "does-not-reject" if float(lb_p) >= 0.05 else "rejects"
        lb_clause = (
            f"Residual Ljung-Box at lag 10 {lb_verdict} "
            f"(p={FMT_P_VALUE.format(float(lb_p))})."
        )
    else:
        lb_clause = "Residual Ljung-Box diagnostic unavailable."
    return (
        f"Auto-ARIMA via pmdarima with {ic} minimization over {n_cand_str} "
        f"under the {search_mode}.{tie_clause} Winner: "
        f"(p,d,q)(P,D,Q)[m] = {order_str}, AIC {aic_str}, BIC {bic_str}. "
        f"{bounds_clause} {lb_clause}"
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


def _trigger_search_scope_narrow(results: dict) -> Optional[str]:
    order = results.get("order")
    max_p = results.get("max_p")
    max_q = results.get("max_q")
    max_d = results.get("max_d")
    if not order:
        return None
    try:
        p, d, q = int(order[0]), int(order[1]), int(order[2])
    except Exception:
        return None
    at_bound = []
    if max_p is not None and p >= int(max_p):
        at_bound.append(("p", p, int(max_p)))
    if max_q is not None and q >= int(max_q):
        at_bound.append(("q", q, int(max_q)))
    if max_d is not None and d >= int(max_d):
        at_bound.append(("d", d, int(max_d)))
    if not at_bound:
        return None
    param, value, bound = at_bound[0]
    return (
        f"Winning {param}={value} sits at the search-bound max_{param}={bound}; "
        f"widening the search may find a better fit."
    )


def _trigger_residuals_non_normal(results: dict) -> Optional[str]:
    """Fix 5 (post-C2 corrections): same semantics as the arima spec's
    trigger — JB rejection flags Gaussian-interval mis-calibration
    risk. auto_arima inherits the diagnostic because both modes share
    ``engine/techniques/arima.py`` and its residual-diagnostic code
    path."""
    jb_p = results.get("jarque_bera_pvalue")
    if jb_p is None or float(jb_p) >= 0.05:
        return None
    return (
        f"Residual normality test rejects at the 5% level "
        f"(JB p={FMT_P_VALUE.format(float(jb_p))}); prediction "
        f"intervals assume Gaussian errors and may be mis-calibrated "
        f"for this series. Consider bootstrapped intervals or a "
        f"heavier-tailed specification."
    )


def _trigger_seasonal_m_inferred(results: dict) -> Optional[str]:
    if not bool(results.get("m_inferred_from_freq", False)):
        return None
    m_val = results.get("seasonal_period_m")
    freq = results.get("frequency", "")
    if not m_val:
        return None
    # Fix 3 (post-C2 corrections batch): when auto_arima selected a
    # zero seasonal component (P=D=Q=0), the search has already
    # concluded no seasonal structure; the "verify inferred m" advice
    # is moot. Suppress the trigger in that case.
    seasonal_order = results.get("seasonal_order") or []
    try:
        if len(seasonal_order) >= 3:
            P, D, Q = int(seasonal_order[0]), int(seasonal_order[1]), int(seasonal_order[2])
            if P == 0 and D == 0 and Q == 0:
                return None
    except Exception:
        pass
    return (
        f"Seasonal period m={int(m_val)} auto-inferred from frequency '{freq}'; "
        f"verify the inferred period matches the intended seasonality."
    )


SPEC = InterpretationSpec(
    technique_id="auto_arima",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_rmse_exceeds_naive,
        _trigger_residual_structure,
        _trigger_residuals_non_normal,
        _trigger_search_scope_narrow,
        _trigger_seasonal_m_inferred,
    ),
    mode_aware=False,
)

register(SPEC)
