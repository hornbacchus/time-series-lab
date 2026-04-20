"""
InterpretationSpec for cross_correlation_lag.

Single-window CCF (contrast with rolling_ccf_lag's rolling-window
variant).
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
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
    bartlett = results.get("bartlett_band")
    n = int(results.get("n_obs", 0))
    corr = interpret_correlation_strength(rho)
    direction = interpret_direction(lag, x, y)
    sign_word = "positive" if rho >= 0 else "negative"
    significant = (
        abs(rho) > float(bartlett) if bartlett is not None else False
    )
    sig_clause = (
        "The peak is Bartlett-band-significant"
        if significant else
        "The peak does NOT exceed the Bartlett significance band"
    )
    return (
        f"{direction['phrase']} with a {corr['band']} {sign_word} "
        f"correlation (ρ={FMT_RHO.format(rho)}) in a static "
        f"{n}-observation window. {sig_clause}; unlike "
        f"rolling_ccf_lag, this is a single-window estimate with no "
        f"regime-stability information."
    )


def _tier2(results: dict) -> str:
    max_lag = int(results.get("max_lag", 12))
    n = int(results.get("n_obs", 0))
    lag = int(results.get("best_lag", 0))
    rho = float(results.get("best_rho", 0.0))
    bartlett = results.get("bartlett_band")
    sig_level = float(results.get("significance", 0.05))
    bart_str = (
        f"Bartlett band (±{float(bartlett):.3f} at {int(round(sig_level * 100))}% level)"
        if bartlett is not None else "Bartlett band in the data tables"
    )
    return (
        f"Static cross-correlation over lags ±{max_lag} on {n} "
        f"observations. Peak ρ={FMT_RHO.format(rho)} at lag {lag} "
        f"vs the {bart_str}. Unlike rolling_ccf_lag, this is a "
        f"single-window estimate; prewhitening (see prewhitened_ccf_lag) "
        f"removes spurious correlations from shared autocorrelation, "
        f"and should be considered if either series is highly "
        f"autocorrelated."
    )


def _trigger_insignificant_peak(results: dict) -> Optional[str]:
    rho = results.get("best_rho")
    bartlett = results.get("bartlett_band")
    if rho is None or bartlett is None:
        return None
    if abs(float(rho)) >= abs(float(bartlett)):
        return None
    return (
        f"Peak |ρ|={FMT_RHO.format(abs(float(rho)))} is below the "
        f"Bartlett band {abs(float(bartlett)):.3f}. No lag is "
        f"statistically significant; the pair may be "
        f"informationally independent at the chosen lag window."
    )


def _trigger_boundary_peak(results: dict) -> Optional[str]:
    lag = results.get("best_lag")
    max_lag = results.get("max_lag")
    if lag is None or max_lag is None:
        return None
    if abs(int(lag)) < int(max_lag):
        return None
    return (
        f"Peak at the boundary lag (±{int(max_lag)}). The true "
        f"optimum may lie outside the search range; widen max_lag "
        f"and re-run before interpreting the current peak."
    )


SPEC = InterpretationSpec(
    technique_id="cross_correlation_lag",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_insignificant_peak, _trigger_boundary_peak),
    mode_aware=False,
)

register(SPEC)
