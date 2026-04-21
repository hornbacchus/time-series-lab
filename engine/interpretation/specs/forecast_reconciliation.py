"""
InterpretationSpec for forecast_reconciliation (hierarchical / grouped
forecasts).

NEW Tier 1 shape — coherence-operation framing (Decision D6). This is a
post-processing operation, NOT a fit technique; Tier 1 leads with
"Reconciled N-level hierarchy..." rather than "Fitted model to...".

Decision D5: primary-method citation convention — MinT-OLS preferred,
bottom_up fallback when OLS covariance is ill-conditioned. The wrapper
exports ``primary_method`` and ``primary_method_fell_back``; the spec
renders accordingly.

Results-dict keys consumed:

    top_series / bottom_series / n_bottom
    methods                      : list[str] methods that ran
    primary_method               : str
    primary_method_fell_back     : bool
    base_forecaster
    horizon / n_observations
    relative_incoherence         : float (0-1)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import format_scale_aware
from interpretation.registry import register

PRESET_GATED_KEYS = ()


_METHOD_DISPLAY = {
    "ols": "MinT-OLS",
    "bottom_up": "bottom-up",
    "top_down": "top-down",
}


def _method_name(method: str) -> str:
    return _METHOD_DISPLAY.get(str(method or "").lower(), str(method or "bottom-up"))


def _tier1(results: dict) -> str:
    top = str(results.get("top_series", "top aggregate"))
    bottom = list(results.get("bottom_series") or [])
    n_bottom = int(results.get("n_bottom", len(bottom)))
    horizon = int(results.get("horizon", 0))
    primary = _method_name(results.get("primary_method"))
    rel_incoh = results.get("relative_incoherence")

    bottom_quoted = ", ".join(f"'{s}'" for s in bottom) if bottom else f"{n_bottom} components"

    if rel_incoh is None:
        incoh_clause = "Historical coherence not reported"
    else:
        try:
            rel = float(rel_incoh)
        except Exception:
            rel = 0.0
        if rel <= 0.01:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level (input hierarchy is coherent)"
            )
        elif rel <= 0.05:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level (mildly incoherent)"
            )
        else:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level — the input hierarchy is "
                f"materially incoherent before reconciliation"
            )

    return (
        f"Reconciled 2-level hierarchy over {horizon} periods: "
        f"'{top}' = sum of {n_bottom} bottom-level series ({bottom_quoted}). "
        f"{primary} reconciliation applied (preferred when available, with "
        f"bottom-up fallback on singular covariance). {incoh_clause}. "
        f"Reconciled forecasts respect the aggregation constraint exactly; "
        f"per-method results disclosed in Tier 2."
    )


def _tier2(results: dict) -> str:
    methods = list(results.get("methods") or [])
    methods_display = [_method_name(m) for m in methods]
    primary = _method_name(results.get("primary_method"))
    fell_back = bool(results.get("primary_method_fell_back", False))
    horizon = int(results.get("horizon", 0))
    base = str(results.get("base_forecaster", "naive"))
    rel_incoh = results.get("relative_incoherence")

    fell_back_clause = ""
    if fell_back:
        fell_back_clause = (
            " MinT-OLS reconciliation failed on this run (singular S'S "
            "covariance); the wrapper fell back to bottom-up reconciliation "
            "and that fallback is cited as the primary method above."
        )

    try:
        rel_pct = float(rel_incoh) * 100 if rel_incoh is not None else None
    except Exception:
        rel_pct = None
    if rel_pct is None:
        incoh_sent = "Historical aggregation residuals not reported."
    else:
        incoh_sent = (
            f"Historical aggregation residuals (pre-reconciliation): "
            f"{rel_pct:.2f}% of the top-level mean."
        )

    return (
        f"Hierarchical forecast reconciliation via linear post-processing. "
        f"{len(methods)} reconciliation method{'s' if len(methods) != 1 else ''} "
        f"applied ({', '.join(methods_display) if methods_display else 'none'}); "
        f"{primary} cited as the primary method when the S'S covariance matrix "
        f"is well-conditioned, with bottom-up fallback otherwise.{fell_back_clause} "
        f"Base forecasts generated via '{base}' over the {horizon}-step horizon; "
        f"reconciliation then projects onto the coherent subspace so that the "
        f"top forecast equals the sum of the bottom forecasts exactly at "
        f"every step. "
        f"{incoh_sent} Reconciliation preserves ranking of base forecasts but "
        f"cannot correct systematic base-forecast bias; if base forecasts are "
        f"poor, reconciled forecasts will also be poor — reconciliation "
        f"enforces coherence only."
    )


def _trigger_historical_incoherence_high(results: dict) -> Optional[str]:
    rel = results.get("relative_incoherence")
    if rel is None:
        return None
    try:
        v = float(rel)
    except Exception:
        return None
    if v <= 0.05:
        return None
    return (
        f"Historical incoherence is {v*100:.1f}% of the top level — the "
        f"input hierarchy does not already add up to the top aggregate. "
        f"Reconciliation will force coherence on the forecasts but the "
        f"underlying data inconsistency should be investigated first; "
        f"reconciliation is not a substitute for data cleaning."
    )


def _trigger_mint_ols_fell_back(results: dict) -> Optional[str]:
    fell_back = bool(results.get("primary_method_fell_back", False))
    if not fell_back:
        return None
    return (
        "MinT-OLS reconciliation failed (singular S'S covariance); the "
        "wrapper fell back to bottom-up. Results are still coherent, but "
        "MinT-OLS's variance-minimization benefit is lost. This typically "
        "happens when the hierarchy has more bottom series than independent "
        "observations, or when bottom series are collinear."
    )


def _trigger_base_forecaster_is_naive_long_horizon(results: dict) -> Optional[str]:
    base = str(results.get("base_forecaster", "")).lower()
    horizon = int(results.get("horizon", 0))
    if base != "naive" or horizon <= 3:
        return None
    return (
        f"Base forecaster is 'naive' (last-value persistence) over a "
        f"{horizon}-step horizon; reconciliation preserves the flat "
        f"trajectory. For a more informative reconciled forecast, "
        f"configure the wrapper to use 'drift' or 'ets' as the base forecaster."
    )


SPEC = InterpretationSpec(
    technique_id="forecast_reconciliation",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_historical_incoherence_high,
        _trigger_mint_ols_fell_back,
        _trigger_base_forecaster_is_naive_long_horizon,
    ),
    mode_aware=False,
)

register(SPEC)
