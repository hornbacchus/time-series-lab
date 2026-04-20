"""
InterpretationSpec for prewhitened_ccf_lag.

CCF on prewhitened residuals. Tier 2 discloses the ARIMA order used
for prewhitening, because the choice affects the interpretation.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_RHO,
    format_series_reference,
    interpret_correlation_strength,
    interpret_direction,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    lag = int(results.get("best_lag", 0))
    rho = float(results.get("best_rho", 0.0))
    arima_order = results.get("prewhiten_arima_order")
    order_str = (
        f"ARIMA{tuple(arima_order)}" if arima_order else "ARIMA"
    )
    corr = interpret_correlation_strength(rho)
    direction = interpret_direction(lag, x, y)
    sign_word = "positive" if rho >= 0 else "negative"
    return (
        f"After prewhitening {format_series_reference(x)} with "
        f"{order_str}, {direction['phrase']} with a {corr['band']} "
        f"{sign_word} correlation (ρ={FMT_RHO.format(rho)}). "
        f"Prewhitening removes {format_series_reference(x)}-side "
        f"autocorrelation so the residual CCF captures genuine cross-"
        f"series lead-lag rather than shared trend."
    )


def _tier2(results: dict) -> str:
    arima_order = results.get("prewhiten_arima_order")
    order_str = (
        f"ARIMA{tuple(arima_order)}" if arima_order else "ARIMA (order not reported)"
    )
    n_post = int(results.get("n_post_prewhitening", 0))
    bartlett = results.get("bartlett_band")
    lag = int(results.get("best_lag", 0))
    rho = float(results.get("best_rho", 0.0))
    lb_p = results.get("residual_ljung_box_p")
    bart_str = (
        f"Bartlett band ±{float(bartlett):.3f}"
        if bartlett is not None else "Bartlett band in the data tables"
    )
    lb_clause = ""
    if lb_p is not None:
        lb_f = float(lb_p)
        if lb_f >= 0.05:
            lb_clause = (
                f" Residual Ljung-Box does-not-reject "
                f"(p={FMT_P_VALUE.format(lb_f)}) — prewhitening adequate."
            )
        else:
            lb_clause = (
                f" Residual Ljung-Box rejects "
                f"(p={FMT_P_VALUE.format(lb_f)}) — prewhitening model "
                f"is misspecified; results may be unreliable."
            )
    return (
        f"Prewhitening model: {order_str} selected; same filter "
        f"applied to the other series. CCF on residuals: peak "
        f"ρ={FMT_RHO.format(rho)} at lag {lag}, {bart_str} on {n_post} "
        f"post-prewhitening observations.{lb_clause} Unlike raw CCF, "
        f"this isolates causal-direction signal from shared "
        f"autocorrelation."
    )


def _trigger_prewhitening_residuals_rejected(results: dict) -> Optional[str]:
    lb_p = results.get("residual_ljung_box_p")
    if lb_p is None or float(lb_p) >= 0.05:
        return None
    return (
        f"Residual Ljung-Box rejects white-noise at the 5% level "
        f"(p={FMT_P_VALUE.format(float(lb_p))}); the prewhitening "
        f"model is misspecified and the residual CCF may inherit "
        f"uncorrected autocorrelation. Refit with a higher-order "
        f"ARIMA or verify the selection criterion."
    )


def _trigger_trivial_prewhitening(results: dict) -> Optional[str]:
    order = results.get("prewhiten_arima_order")
    if not order:
        return None
    p, d, q = (int(x) for x in order[:3])
    if p != 0 or d != 0 or q != 0:
        return None
    return (
        "Prewhitening model selected ARIMA(0,0,0) — the series has no "
        "detectable autocorrelation. Prewhitening was unnecessary; "
        "raw CCF would give the same answer with less computational "
        "cost."
    )


SPEC = InterpretationSpec(
    technique_id="prewhitened_ccf_lag",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_prewhitening_residuals_rejected,
        _trigger_trivial_prewhitening,
    ),
    mode_aware=False,
)

register(SPEC)
