"""
InterpretationSpec for mstl_decompose.

Tier 1 leads with per-period seasonal strengths and trend strength,
identifying which cycle dominates. Tier 2 discloses the nested-STL
method and the additive-only restriction.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_RHO,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _strength_band(v: float) -> str:
    v = float(v)
    if v < 0.3:
        return "weak"
    if v < 0.6:
        return "moderate"
    if v < 0.9:
        return "strong"
    return "very strong"


def _period_name(p: int) -> str:
    if p == 24:
        return "daily"
    if p == 168:
        return "weekly"
    if p == 12:
        return "monthly"
    if p == 7:
        return "weekly"
    if p == 4:
        return "quarterly"
    return f"period-{int(p)}"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    periods = list(results.get("periods") or [])
    seasonal_strengths = list(results.get("seasonal_strengths") or [])
    Ft = float(results.get("trend_strength", 0.0))
    # Describe each seasonality
    parts = []
    dominant_idx = None
    dominant_val = -1.0
    for i, p in enumerate(periods):
        s = float(seasonal_strengths[i]) if i < len(seasonal_strengths) else 0.0
        parts.append(f"{_period_name(int(p))} {FMT_RHO.format(s)} ({_strength_band(s)})")
        if s > dominant_val:
            dominant_val = s
            dominant_idx = i
    strengths_text = "; ".join(parts) if parts else "no seasonal components detected"
    dominant_desc = (
        _period_name(int(periods[dominant_idx]))
        if dominant_idx is not None and periods
        else "no dominant"
    )
    return (
        f"MSTL decomposition of {format_series_reference(name)} "
        f"({n} observations, periods {list(periods)}). Seasonal "
        f"strengths: {strengths_text}; trend strength "
        f"{FMT_RHO.format(Ft)} ({_strength_band(Ft)}). The "
        f"{dominant_desc} cycle dominates; all named seasonalities are "
        f"required for an accurate decomposition."
    )


def _tier2(results: dict) -> str:
    periods = list(results.get("periods") or [])
    return (
        f"Multi-seasonal STL with additive components. Each seasonal "
        f"component is extracted via nested STL passes in order "
        f"{list(periods)}; strengths computed independently per "
        f"period. The trend strength reflects the residual-adjusted "
        f"joint trend across all seasonal passes. MSTL does not "
        f"support multiplicative decomposition — log-transform inputs "
        f"if multiplicative behavior is suspected."
    )


def _trigger_negligible_seasonality(results: dict) -> Optional[str]:
    periods = list(results.get("periods") or [])
    seasonal_strengths = list(results.get("seasonal_strengths") or [])
    for i, p in enumerate(periods):
        s = float(seasonal_strengths[i]) if i < len(seasonal_strengths) else 0.0
        if s < 0.1:
            return (
                f"The {_period_name(int(p))} seasonality has strength "
                f"{FMT_RHO.format(s)}, near zero. Drop this period from "
                f"the period list and refit; MSTL benefits from "
                f"retaining only the genuinely periodic components."
            )
    return None


def _trigger_harmonic_periods(results: dict) -> Optional[str]:
    periods = [int(p) for p in (results.get("periods") or [])]
    strengths = [float(s) for s in (results.get("seasonal_strengths") or [])]
    for i in range(len(periods) - 1):
        for j in range(i + 1, len(periods)):
            if i >= len(strengths) or j >= len(strengths):
                continue
            if strengths[i] < 0.7 or strengths[j] < 0.7:
                continue
            p_i, p_j = periods[i], periods[j]
            if p_i <= 0 or p_j <= 0:
                continue
            ratio = max(p_i, p_j) / min(p_i, p_j)
            if ratio <= 2.0:
                return (
                    f"Periods {p_i} and {p_j} both carry strong seasonality "
                    f"with a ratio within 2× — one may be a harmonic of "
                    f"the other rather than a distinct cycle. Review the "
                    f"period list for degeneracy."
                )
    return None


SPEC = InterpretationSpec(
    technique_id="mstl_decompose",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_negligible_seasonality, _trigger_harmonic_periods),
    mode_aware=False,
)

register(SPEC)
