"""
InterpretationSpec for tar_setar (threshold AR / self-exciting).

Tier 1 leads with threshold value + delay + linearity-test verdict.
Per V4: Tier 1 closer is actionable.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_SIGNED,
    FMT_F_STAT,
    FMT_P_VALUE,
    format_series_reference,
    interpret_pvalue,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n_regimes = int(results.get("n_regimes", 2))
    thresholds = list(results.get("thresholds") or [])
    threshold_str = ", ".join(FMT_COEF_SIGNED.format(float(t)) for t in thresholds) or "?"
    delay = int(results.get("delay", 1))
    linearity_f = results.get("linearity_f_stat")
    linearity_p = results.get("linearity_p_value")
    regime_1_share = results.get("regime_1_share")
    f_clause = ""
    if linearity_f is not None and linearity_p is not None:
        p_f = float(linearity_p)
        verdict_word = "rejects linear AR" if p_f < 0.05 else "does not reject linear AR"
        f_clause = (
            f"Linearity test F={FMT_F_STAT.format(float(linearity_f))} "
            f"(p={FMT_P_VALUE.format(p_f)}) {verdict_word} at 5% — "
            f"threshold structure is "
            f"{'statistically meaningful' if p_f < 0.05 else 'weak'}."
        )
    regime_clause = ""
    if regime_1_share is not None:
        regime_clause = (
            f"Regime 1 (y(t-{delay}) ≤ threshold) dominates with "
            f"{100.0 * float(regime_1_share):.0f}% of observations."
        )
    closer = (
        "Consider regime-conditional inference for any signal "
        "extracted from this series; threshold dynamics mean pooled "
        "estimates can hide regime-specific behavior."
    )
    return (
        f"SETAR({n_regimes}) on {format_series_reference(name)} with "
        f"threshold at {threshold_str} on y(t-{delay}). {f_clause} "
        f"{regime_clause} {closer}"
    )


def _tier2(results: dict) -> str:
    thresholds = list(results.get("thresholds") or [])
    threshold_str = ", ".join(FMT_COEF_SIGNED.format(float(t)) for t in thresholds) or "?"
    delay = int(results.get("delay", 1))
    n_obs = int(results.get("n_obs", 0))
    per_regime_rows = []
    regimes_info = results.get("regimes_info") or []
    for i, r in enumerate(regimes_info):
        try:
            n = int(r.get("n_obs", 0))
            sigma = float(r.get("sigma", 0.0))
            per_regime_rows.append(
                f"Regime {i + 1}: {n} obs, σ={FMT_COEF_SIGNED.format(sigma) if sigma < 0 else FMT_F_STAT.format(sigma)}"
            )
        except Exception:
            continue
    per_regime_clause = (
        "; ".join(per_regime_rows) + "."
        if per_regime_rows else "Per-regime parameters in the data tables."
    )
    return (
        f"Self-exciting threshold AR with threshold(s) y(t-{delay}) "
        f"= {threshold_str} estimated by grid search minimizing total "
        f"sum-of-squared-residuals on {n_obs} observations. "
        f"{per_regime_clause} Linearity test compares against a "
        f"single-regime AR null via conditional F. Unlike STAR, the "
        f"transition is discrete; unlike Markov Switching, the "
        f"triggering variable is observable."
    )


def _trigger_weak_linearity_test(results: dict) -> Optional[str]:
    p = results.get("linearity_p_value")
    if p is None or float(p) <= 0.10:
        return None
    return (
        f"Linearity test p-value {FMT_P_VALUE.format(float(p))} "
        f"exceeds 0.10 — threshold effect is weak. A linear AR may "
        f"suffice; the SETAR complexity is not earning itself."
    )


def _trigger_imbalanced_regimes(results: dict) -> Optional[str]:
    regimes_info = results.get("regimes_info") or []
    n_total = sum(int(r.get("n_obs", 0) or 0) for r in regimes_info)
    if n_total == 0:
        return None
    for i, r in enumerate(regimes_info):
        n = int(r.get("n_obs", 0) or 0)
        share = n / n_total
        if share < 0.15:
            return (
                f"Regime {i + 1} contains {100.0 * share:.0f}% of "
                f"observations. Imbalanced regime counts make "
                f"coefficient estimates unstable; consider a "
                f"different threshold or a two-regime specification "
                f"if running SETAR(3)."
            )
    return None


def _trigger_underpopulated_inner_regime(results: dict) -> Optional[str]:
    n_regimes = int(results.get("n_regimes", 2))
    if n_regimes < 3:
        return None
    regimes_info = results.get("regimes_info") or []
    n_total = sum(int(r.get("n_obs", 0) or 0) for r in regimes_info)
    if n_total == 0 or len(regimes_info) < 2:
        return None
    # Inner regime is the middle one for n_regimes=3.
    inner_idx = 1
    if inner_idx >= len(regimes_info):
        return None
    n_inner = int(regimes_info[inner_idx].get("n_obs", 0) or 0)
    share = n_inner / n_total
    if share >= 0.10:
        return None
    return (
        f"Inner regime (between the two thresholds) contains only "
        f"{100.0 * share:.0f}% of observations. Consider a 2-regime "
        f"SETAR; the 3-regime specification's middle regime is "
        f"underpopulated."
    )


SPEC = InterpretationSpec(
    technique_id="tar_setar",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_weak_linearity_test,
        _trigger_imbalanced_regimes,
        _trigger_underpopulated_inner_regime,
    ),
    mode_aware=False,
)

register(SPEC)
