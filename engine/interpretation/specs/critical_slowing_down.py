"""Interpretation contract for critical_slowing_down.

5-trigger interpretation spec for the CSD early-warning detector.
Triggers fire on:
  D-CSD-1 composite_elevated      — composite EWS in elevated/critical band
  D-CSD-2 consistent_tau_pattern  — both AR(1) AND variance show
                                    significant rising trend
  D-CSD-3 post_transition         — tail residuals indicate already-
                                    shifted regime
  D-CSD-4 insufficient_data       — series too short for stable
                                    estimation
  D-CSD-5 non_stationary_residuals — detrending residuals fail ADF

Methodology caveats are first-class output in Tier 2 (Phase 1
design lock). Honest disclosure: predictive value out-of-sample
on financial market data is contested in the empirical literature.
"""

from __future__ import annotations

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register


# ─────────────────────────────────────────────────────
# Tier 1 — single-sentence summary
# ─────────────────────────────────────────────────────

def _tier1(results: dict) -> str:
    """Single-sentence summary of CSD detection result."""
    audit = results.get("audit_fields", {}) or {}
    state = audit.get("ews_state", "unknown")
    score = audit.get("ews_composite_score")

    if state == "critical":
        score_str = f"{float(score):.2f}sigma" if score is not None else "n/a"
        return (
            f"Critical Slowing Down indicators are in CRITICAL "
            f"state (composite EWS score = {score_str}). The "
            f"series shows statistical signatures consistent "
            f"with approaching a phase transition."
        )
    elif state == "elevated":
        score_str = f"{float(score):.2f}sigma" if score is not None else "n/a"
        return (
            f"Critical Slowing Down indicators are ELEVATED "
            f"(composite EWS score = {score_str}). Some -- but "
            f"not all -- indicators show patterns consistent "
            f"with rising instability."
        )
    elif state == "normal":
        score_str = f"{float(score):.2f}sigma" if score is not None else "n/a"
        return (
            f"Critical Slowing Down indicators are NORMAL "
            f"(composite EWS score = {score_str}). The series "
            f"does not show statistical signatures of an "
            f"approaching transition."
        )
    else:
        return (
            "Critical Slowing Down analysis did not complete; "
            "see Tier 3 triggers for diagnostics."
        )


# ─────────────────────────────────────────────────────
# Tier 2 — multi-paragraph methodology + result narrative
# ─────────────────────────────────────────────────────

def _tier2(results: dict) -> str:
    """Multi-paragraph methodology disclosure + result narrative."""
    audit = results.get("audit_fields", {}) or {}
    status = results.get("status")

    # Insufficient-data short-circuit
    if status == "insufficient_data":
        return (
            "CSD analysis did not complete: input series too "
            "short for stable estimation. See Tier 3 trigger "
            "for specific data-length recommendations."
        )

    # Build estimation_clause
    detrending_method = audit.get("detrending_method") or "unknown"
    estimation_clause = (
        f"CSD analysis applied {detrending_method} detrending"
    )
    if detrending_method == "gaussian":
        bw = audit.get("detrending_bandwidth")
        if bw is not None:
            estimation_clause += (
                f" (Gaussian kernel sigma = {float(bw):.2f} samples)"
            )
    rolling_window = audit.get("rolling_window")
    kendall_lookback = audit.get("kendall_lookback")
    if rolling_window is not None and kendall_lookback is not None:
        estimation_clause += (
            f" with rolling window = {int(rolling_window)} and "
            f"Kendall tau computed over a "
            f"{int(kendall_lookback)}-point trailing window."
        )
    else:
        estimation_clause += "."
    if audit.get("compute_pvalues"):
        n_surr = audit.get("n_surrogates")
        if n_surr is not None:
            estimation_clause += (
                f" Statistical significance was assessed via "
                f"{int(n_surr)} AR(1)-bootstrap surrogates."
            )
    else:
        estimation_clause += (
            " Statistical significance was assessed via "
            "asymptotic Kendall tau p-values "
            "(compute_pvalues was disabled)."
        )

    # Build per-indicator narrative
    indicators = (
        "ar1", "variance", "skewness", "kurtosis",
        "return_rate", "density_ratio",
    )
    indicator_clauses = []
    for ind in indicators:
        tau = audit.get(f"tau_{ind}")
        pval = audit.get(f"tau_{ind}_pvalue")
        if tau is None or pval is None:
            continue
        sig = "significant" if float(pval) < 0.05 else "not significant"
        sign = "rising" if float(tau) > 0 else "falling"
        label = ind.replace("_", " ")
        indicator_clauses.append(
            f"{label}: tau = {float(tau):+.3f} "
            f"({sign}, p = {float(pval):.3f}, {sig})"
        )
    if indicator_clauses:
        indicator_block = (
            "Per-indicator Kendall tau values: "
            + "; ".join(indicator_clauses) + "."
        )
    else:
        indicator_block = ""

    # Methodology caveats — first-class output (Phase 1 design lock)
    caveat_block = (
        "Methodological caveats: (1) CSD signals are descriptive "
        "of approaching transitions in dynamical-systems theory, "
        "but their predictive value out-of-sample on financial "
        "market data is contested in the empirical literature "
        "(see Diks-Hommes-Wang 2018, who find mixed results on "
        "real financial crises). (2) Detrending bandwidth choice "
        "materially affects results -- a different bandwidth may "
        "yield different EWS conclusions. (3) Rising variance "
        "can also signal volatility clustering without any phase "
        "transition. (4) Kendall tau on rolling indicators has "
        "known limitations on trending or cyclical underlying "
        "series."
    )

    # Post-transition disambiguation
    post_transition_block = ""
    if audit.get("post_transition_indicated"):
        skew = audit.get("tail_skewness")
        kurt = audit.get("tail_kurtosis")
        skew_str = f"{float(skew):+.2f}" if skew is not None else "n/a"
        kurt_str = f"{float(kurt):+.2f}" if kurt is not None else "n/a"
        post_transition_block = (
            f" The tail residuals show high skewness "
            f"({skew_str}) or kurtosis ({kurt_str}), which may "
            "indicate the series has already undergone a regime "
            "shift rather than approaching one -- CSD indicators "
            "are most reliable in pre-transition regimes."
        )

    # Detrending-residuals stationarity disclosure
    stationarity_block = ""
    if audit.get("detrending_residuals_stationary") is False:
        adf_p = audit.get("detrending_residuals_adf_pvalue")
        adf_str = f"{float(adf_p):.3f}" if adf_p is not None else "n/a"
        stationarity_block = (
            f" Detrending residuals failed the ADF stationarity "
            f"test (p = {adf_str}); CSD-pipeline assumptions "
            "require stationary residuals, so results should be "
            "interpreted with caution. Consider an alternative "
            "detrending method or a longer Gaussian kernel "
            "bandwidth."
        )

    parts = [estimation_clause]
    if indicator_block:
        parts.append(indicator_block)
    parts.append(caveat_block)
    if post_transition_block:
        parts.append(post_transition_block.strip())
    if stationarity_block:
        parts.append(stationarity_block.strip())
    return " ".join(parts)


# ─────────────────────────────────────────────────────
# Tier 3 triggers (5)
# ─────────────────────────────────────────────────────

def _trigger_composite_elevated(results: dict) -> Optional[str]:
    """D-CSD-1 -- composite EWS score is elevated or critical."""
    audit = results.get("audit_fields", {}) or {}
    state = audit.get("ews_state")
    score = audit.get("ews_composite_score")
    if state not in ("elevated", "critical"):
        return None
    if score is None:
        return None
    severity = "CRITICAL" if state == "critical" else "ELEVATED"
    return (
        f"Composite EWS score in {severity} regime "
        f"({float(score):+.2f}sigma above null). The Kendall tau "
        f"values across rolling CSD indicators show a "
        f"statistically meaningful trend pattern consistent "
        f"with approaching a phase transition. This is a "
        f"descriptive statistical finding, not a forecast -- "
        f"interpret in conjunction with the methodological "
        f"caveats in Tier 2 disclosure. For investment use, "
        f"treat as one input among several regime-detection "
        f"signals rather than a standalone trading signal."
    )


def _trigger_consistent_tau_pattern(results: dict) -> Optional[str]:
    """D-CSD-2 -- both AR(1) and variance show significant rising
    Kendall tau (the strictest historical predictor in Dakos work)."""
    audit = results.get("audit_fields", {}) or {}
    tau_ar1 = audit.get("tau_ar1")
    tau_var = audit.get("tau_variance")
    p_ar1 = audit.get("tau_ar1_pvalue")
    p_var = audit.get("tau_variance_pvalue")
    if (tau_ar1 is None or tau_var is None
            or p_ar1 is None or p_var is None):
        return None
    if not (
        float(tau_ar1) > 0 and float(tau_var) > 0
        and float(p_ar1) < 0.05 and float(p_var) < 0.05
    ):
        return None
    return (
        f"Both lag-1 autocorrelation (tau = {float(tau_ar1):+.3f}, "
        f"p = {float(p_ar1):.3f}) AND variance "
        f"(tau = {float(tau_var):+.3f}, p = {float(p_var):.3f}) "
        f"show statistically significant rising trends. This is "
        f"the strictest CSD pattern in the Dakos 2012 framework -- "
        f"both primary indicators agreeing increases confidence "
        f"that the underlying system is approaching a transition "
        f"rather than experiencing transient volatility. "
        f"Consistent rising AR(1) reflects slower recovery from "
        f"perturbations; consistent rising variance reflects "
        f"accumulating shock impacts."
    )


def _trigger_post_transition(results: dict) -> Optional[str]:
    """D-CSD-3 -- post-transition disambiguation."""
    audit = results.get("audit_fields", {}) or {}
    if not audit.get("post_transition_indicated"):
        return None
    skew = audit.get("tail_skewness")
    kurt = audit.get("tail_kurtosis")
    if skew is None or kurt is None:
        return None
    return (
        f"Tail residuals show elevated skewness "
        f"({float(skew):+.2f}) or kurtosis "
        f"({float(kurt):+.2f}), suggesting the series may have "
        f"already undergone a regime shift rather than "
        f"approaching one. CSD indicators are most reliable as "
        f"early warnings in pre-transition regimes; in "
        f"post-transition regimes they may show residual "
        f"signals from the recent shift but lose predictive "
        f"interpretation. Consider examining the underlying "
        f"series visually for evidence of a recent discontinuity "
        f"or level shift."
    )


def _trigger_insufficient_data(results: dict) -> Optional[str]:
    """D-CSD-4 -- insufficient data for stable CSD estimation."""
    audit = results.get("audit_fields", {}) or {}
    status = results.get("status")
    if status != "insufficient_data":
        return None
    T = audit.get("series_length")
    T_str = str(int(T)) if T is not None else "?"
    return (
        f"Input series of length {T_str} is too short for stable "
        f"CSD estimation given the rolling window and Kendall "
        f"lookback parameters. CSD literature recommends at "
        f"least T = 500 for reliable indicator trends, with "
        f"longer series (T > 1000) preferred for surrogate-based "
        f"significance testing. Consider using a longer data "
        f"window or shortening the rolling-window parameter."
    )


def _trigger_non_stationary_residuals(results: dict) -> Optional[str]:
    """D-CSD-5 -- detrending residuals failed stationarity check."""
    audit = results.get("audit_fields", {}) or {}
    if audit.get("detrending_residuals_stationary") is None:
        return None  # not computed (e.g., insufficient_data path)
    if audit.get("detrending_residuals_stationary"):
        return None  # was stationary, no trigger
    p = audit.get("detrending_residuals_adf_pvalue")
    method = audit.get("detrending_method")
    if p is None or method is None:
        return None
    return (
        f"Detrending residuals failed the ADF stationarity test "
        f"(p = {float(p):.3f}) using {method} detrending. The "
        f"CSD pipeline assumes stationary residuals; "
        f"non-stationary residuals produce spurious trends in "
        f"the rolling indicators that can mimic CSD without an "
        f"actual underlying transition. Recommended actions: "
        f"(a) try an alternative detrending method; (b) increase "
        f"the Gaussian kernel bandwidth if currently using "
        f"gaussian; (c) examine the input series for outliers or "
        f"structural breaks that may need preprocessing."
    )


# ─────────────────────────────────────────────────────
# SPEC registration
# ─────────────────────────────────────────────────────

SPEC = InterpretationSpec(
    technique_id="critical_slowing_down",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_composite_elevated,
        _trigger_consistent_tau_pattern,
        _trigger_post_transition,
        _trigger_insufficient_data,
        _trigger_non_stationary_residuals,
    ),
    mode_aware=False,
)

register(SPEC)
