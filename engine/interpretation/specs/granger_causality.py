"""
InterpretationSpec for Granger causality.

Voice: Register C (analyst-briefing hybrid), locked in Prompt A and
propagated through Prompt B. Every Tier 1 ends with an actionable
next step. Greek letters are permitted in Tier 1 only in citation
form (T4 update); Granger phrasings carry no Greek.

Results-dict keys consumed by this spec (assembled by
``granger_causality.py`` before the ``make_response`` call):

    series_name_x   : str (the "cause" series — test is X → Y)
    series_name_y   : str (the "effect" series)
    best_lag        : int
    best_f          : float
    best_p          : float
    max_lag         : int
    n_obs           : int
    significance    : float (α used for the verdict)
    reverse_f       : float or None (only when preset == "Thorough")
    reverse_p       : float or None
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_pvalue,
    format_stat_technical,
    FMT_F_STAT,
    FMT_P_VALUE,
)
from interpretation.registry import register


# Preset-gated input-dict keys (T11 invariant). These keys are only
# populated under certain presets — the reverse-direction Granger test
# runs only on the Thorough preset. Tier 1 / Tier 2 must branch on
# presence rather than assert unconditional claims.
PRESET_GATED_KEYS = ("reverse_f", "reverse_p")


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    best_p = float(results.get("best_p", 1.0))
    best_f = float(results.get("best_f", 0.0))
    best_lag = int(results.get("best_lag", 0))
    significance = float(results.get("significance", 0.05))

    pband = interpret_pvalue(best_p)
    rejected = pband["strength"] in ("strong", "standard", "marginal")

    # p-value rendering: "<0.001" for strongly-rejecting cases, exact
    # otherwise. The ADF spec established this convention.
    if best_p < 1e-3:
        p_str = "p<0.001"
    else:
        p_str = f"p={best_p:.2f}" if best_p >= 0.01 else f"p={best_p:.3f}"

    # Preset-gated reverse-direction claim (§4.4, T11). We branch on
    # whether the reverse test actually ran — Fast preset omits it, so
    # Tier 1 must not assert a reverse-direction result it doesn't have.
    reverse_f = results.get("reverse_f")
    reverse_p = results.get("reverse_p")
    reverse_tested = reverse_f is not None and reverse_p is not None
    reverse_rejected = (
        reverse_tested and float(reverse_p) < significance
    )

    if rejected:
        if not reverse_tested:
            return (
                f"Past values of '{x}' significantly predict '{y}' at lag "
                f"{best_lag} (F={best_f:.2f}, {p_str}). The reverse "
                f"direction ('{y}' → '{x}') was not tested at this preset; "
                f"a Thorough-preset rerun would confirm whether the "
                f"information flow is one-way rather than bidirectional."
            )
        if reverse_rejected:
            rev_f = float(reverse_f)
            return (
                f"Both '{x}' → '{y}' and '{y}' → '{x}' are significant "
                f"(forward F={best_f:.2f}, reverse F={rev_f:.2f}), "
                f"indicating a feedback loop rather than one-way "
                f"causation. Treat the pair as a coupled bidirectional "
                f"system; a reduced-form VAR captures both directions "
                f"jointly."
            )
        return (
            f"Past values of '{x}' significantly predict '{y}' at lag "
            f"{best_lag} (F={best_f:.2f}, {p_str}). The reverse channel "
            f"is not significant, consistent with one-way information "
            f"flow from '{x}' to '{y}'. Incorporate '{x}' lags when "
            f"forecasting '{y}'; the reverse does not carry symmetric "
            f"predictive content."
        )

    # Best-lag does not reject
    max_lag = int(results.get("max_lag", 0))
    if not reverse_tested:
        return (
            f"Past values of '{x}' do not significantly predict '{y}' at "
            f"any lag through {max_lag} (best F={best_f:.2f}, {p_str}). "
            f"The reverse direction was not tested at this preset; a "
            f"Thorough-preset rerun would confirm whether the pair is "
            f"informationally independent in both directions."
        )
    if reverse_rejected:
        rev_f = float(reverse_f)
        return (
            f"Past values of '{x}' do not significantly predict '{y}' "
            f"(best F={best_f:.2f}, {p_str}), but the reverse direction "
            f"('{y}' → '{x}') does reject at lag {best_lag} "
            f"(F={rev_f:.2f}). Incorporate '{y}' lags when forecasting "
            f"'{x}'; the forward direction carries no symmetric "
            f"predictive content."
        )
    return (
        f"Past values of '{x}' do not significantly predict '{y}' at any "
        f"lag through {max_lag} (best F={best_f:.2f}, {p_str}). The "
        f"reverse direction is also non-significant. Treat the two "
        f"series as informationally independent for forecasting purposes."
    )


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    n_obs = int(results.get("n_obs", 0))
    max_lag = int(results.get("max_lag", 0))
    best_p = float(results.get("best_p", 1.0))
    best_f = float(results.get("best_f", 0.0))
    best_lag = int(results.get("best_lag", 0))
    significance = float(results.get("significance", 0.05))
    reverse_f = results.get("reverse_f")
    reverse_p = results.get("reverse_p")

    pband = interpret_pvalue(best_p)
    rejected = pband["strength"] in ("strong", "standard", "marginal")

    # Header + disclosure
    header = (
        f"Granger F-test on '{x}' → '{y}' across lags 1–{max_lag} "
        f"(n={n_obs})."
    )
    disclosure = (
        "Lag augmentation controls for serial correlation in the "
        "regressors; the F-statistic assumes approximately iid residuals "
        "of the augmented VAR."
    )

    if rejected:
        # Strongest-evidence sentence
        sig_pct = int(round(pband["band_upper"] * 100))
        evidence = (
            f"The strongest evidence appears at lag {best_lag} "
            f"({format_stat_technical('F', best_f, p_value=best_p)}), "
            f"exceeding the {sig_pct}% critical threshold."
        )
        # Reverse-direction citation — branch on whether the reverse
        # test was run AND whether it rejected. Three cases per §4.4.
        if reverse_f is None or reverse_p is None:
            reverse_clause = (
                "The reverse-direction test was not run at this preset; "
                "a Thorough-preset rerun would confirm whether the "
                "channel is strictly one-way."
            )
        elif float(reverse_p) < significance:
            reverse_clause = (
                f"The reverse-direction test ('{y}' → '{x}') also rejects "
                f"({format_stat_technical('F', float(reverse_f), p_value=float(reverse_p))}), "
                f"indicating bidirectional causality rather than one-way "
                f"information flow."
            )
        else:
            reverse_clause = (
                f"The reverse-direction test ('{y}' → '{x}') fails to "
                f"reject ({format_stat_technical('F', float(reverse_f), p_value=float(reverse_p))}), "
                f"which rules out feedback from '{y}' at any tested lag."
            )
        return f"{header} {disclosure} {evidence} {reverse_clause}"

    # Not rejected
    strongest = (
        f"The strongest lag yields {format_stat_technical('F', best_f, p_value=best_p)}, "
        f"well short of conventional rejection thresholds."
    )
    if reverse_f is None or reverse_p is None:
        reverse_clause = (
            "The reverse-direction test was not run at this preset."
        )
    elif float(reverse_p) < significance:
        reverse_clause = (
            f"The reverse-direction test ('{y}' → '{x}') does reject, "
            f"however ({format_stat_technical('F', float(reverse_f), p_value=float(reverse_p))}); "
            f"information flows the other way."
        )
    else:
        reverse_clause = (
            f"The reverse-direction test gives the same verdict "
            f"({format_stat_technical('F', float(reverse_f), p_value=float(reverse_p))})."
        )
    return f"{header} {disclosure} {strongest} {reverse_clause}"


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_bidirectional(results: dict) -> Optional[str]:
    """Fires when both the forward and reverse tests reject (bidirectional
    Granger causality)."""
    best_p = float(results.get("best_p", 1.0))
    reverse_p = results.get("reverse_p")
    significance = float(results.get("significance", 0.05))
    if reverse_p is None:
        return None
    if best_p >= significance or float(reverse_p) >= significance:
        return None
    rev_f = float(results.get("reverse_f", 0.0))
    return (
        f"Reverse-direction test also rejects ({FMT_F_STAT.format(rev_f)}, "
        f"{FMT_P_VALUE.format(float(reverse_p))}); treat this as "
        "bidirectional Granger causality, which typically indicates a "
        "feedback loop rather than a one-way causal chain."
    )


def _trigger_borderline_p(results: dict) -> Optional[str]:
    """Fires when the best-lag p-value sits within the 4%-6% band."""
    best_p = float(results.get("best_p", 1.0))
    if not (0.04 < best_p < 0.06):
        return None
    direction = "stricter (1%)" if best_p < 0.05 else "looser (10%)"
    return (
        f"The best-lag p-value ({best_p:.3f}) sits near the 5% threshold "
        f"— the causality verdict is sensitive to the chosen significance "
        f"level and would change under a {direction} cutoff."
    )


def _trigger_small_sample(results: dict) -> Optional[str]:
    """Fires when n < 50."""
    n_obs = int(results.get("n_obs", 0))
    if n_obs >= 50:
        return None
    return (
        f"Sample size is small (n={n_obs}); Granger F-tests have limited "
        "power in this range. Treat the verdict as provisional."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="granger_causality",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_bidirectional,
        _trigger_borderline_p,
        _trigger_small_sample,
    ),
    mode_aware=False,
)

register(SPEC)
