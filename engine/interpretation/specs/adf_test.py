"""
InterpretationSpec for the Augmented Dickey-Fuller test (and its
joint-triage mode that runs ADF + KPSS + PP together).

Voice convention for Tier 1 / Tier 2 / Tier 3 (Register C,
analyst-briefing hybrid) was locked in Prompt A Phase 2. Every one of
the 67 technique specs that Prompts B and C will add must inherit the
same register.

Greek-letter convention:
    Tier 1: NO Greek letters. Plain English only. This is enforced by
            the T4 invariant.
    Tier 2: Greek letters ALLOWED where they communicate the
            statistical machinery faithfully (ρ close to 1, etc.).
    Tier 3: Greek letters allowed at author's discretion.

The three reference cases baked into this spec (and canonically tested
in ``engine/tests/test_interpretation_contract.py``):

    (a) Clear stationary — e.g., Real GDP Q/Q SAAR, single-test mode.
    (b) Clear unit root — e.g., random walk, triage mode, joint verdict
        UNIT ROOT (I(1)).
    (c) CONFLICTING — ADF rejects AND KPSS rejects, joint verdict
        CONFLICTING.

Results-dict keys consumed by this spec (assembled by adf_test.py's
wrapper before the ``make_response`` call):

    Required in all modes:
        mode               : "single_test" | "triage"
        series_name        : str
        adf_stat           : float
        p_value            : float      (ADF p)
        regression         : "c" | "ct" | "ctt" | "n"
        used_lag           : int        (AIC-selected)
        schwert_bound      : int
        n_obs              : int
        crit_1pct          : float      (critical value at 1%)
        crit_5pct          : float      (critical value at 5%)
        significance_level : float      (α)
        trending           : bool       (from adf_test._detect_trend)
        t_stat_trend       : float      (from _detect_trend)
        decision_rejected  : bool       (ADF null rejected)

    Required in triage mode:
        kpss_stat, kpss_pvalue, kpss_rejected
        pp_stat,   pp_pvalue,   pp_rejected
        joint_verdict      : "STATIONARY" | "UNIT ROOT (I(1))" |
                             "CONFLICTING" | "INCONCLUSIVE" | "ERROR"
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_pvalue,
    format_stat_technical,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


# ---------------------------------------------------------------------
# Tier 1 — Plain-Language Finding
# ---------------------------------------------------------------------


def _tier1(results: dict) -> str:
    """Choose one of three reference paths based on joint verdict.

    Single-test mode resolves as either (a) stationary or (b) unit
    root. Triage mode adds (c) CONFLICTING and a fourth INCONCLUSIVE
    path. Every return value ends with an actionable next step
    (Register C consistency).
    """
    mode = results.get("mode", "single_test")
    name = _series_ref(results)

    if mode == "triage":
        verdict = results.get("joint_verdict", "")
        if verdict == "STATIONARY":
            return (
                f"{name} is stationary — shocks decay rather than accumulating. "
                "The series can be used directly in regressions, VAR, and "
                "other stationarity-assuming models without first-differencing."
            )
        if verdict == "UNIT ROOT (I(1))":
            return (
                f"{name} has a unit root — shocks accumulate rather than "
                "dissipating. Differencing is required before use in "
                "stationary models such as ARIMA or VAR. For modeling the "
                "level directly, a cointegration or state-space framework "
                "is needed."
            )
        if verdict == "CONFLICTING":
            return (
                f"For {name}, the two stationarity tests disagree: ADF "
                "rejects the unit root while KPSS also rejects stationarity. "
                "This pattern typically signals a structural break, a regime "
                "change, or a near-unit-root process. Recommended follow-up: "
                "split the sample and re-run the triage on each segment, or "
                "use Zivot-Andrews for an unknown-break-point test."
            )
        if verdict == "INCONCLUSIVE":
            return (
                f"For {name}, neither test rejects its null — the data do not "
                "pin down a verdict. This usually reflects limited sample "
                "size or a near-unit-root process that is statistically "
                "indistinguishable from both stationarity and a unit root. "
                "Recommended follow-up: provide more observations, try "
                "regression='ct' if the series may be trending, or treat the "
                "series as I(1) under caution."
            )
        # Verdict is "ERROR" or unrecognized — fall through to the
        # neutral placeholder. Tier 2 will carry the error detail.
        return (
            f"The stationarity triage for {name} could not complete. See the "
            "Technical Interpretation for the specific error and Results "
            "tables for the raw per-test output."
        )

    # Single-test mode: (a) clear stationary, (b) clear unit root.
    rejected = bool(results.get("decision_rejected"))
    if rejected:
        return (
            f"{name} is stationary — shocks decay rather than accumulating. "
            "The series can be used directly in regressions, VAR, and other "
            "stationarity-assuming models without first-differencing."
        )
    return (
        f"{name} has a unit root — shocks accumulate rather than "
        "dissipating. Differencing is required before use in stationary "
        "models such as ARIMA or VAR. For modeling the level directly, a "
        "cointegration or state-space framework is needed."
    )


def _series_ref(results: dict) -> str:
    """Compose the opening series reference used by Tier 1 / Tier 2.

    Names come in quoted in the wrapper; the reference layer keeps the
    quotes so user-facing strings consistently cite the series as
    "'Real GDP Q/Q SAAR'" rather than ambiguous bare text.
    """
    name = str(results.get("series_name", "The series"))
    if not name.startswith("'"):
        name = f"'{name}'"
    return name


# ---------------------------------------------------------------------
# Tier 2 — Technical Interpretation
# ---------------------------------------------------------------------


_REGRESSION_LABEL = {
    "c":   "constant-only",
    "ct":  "constant + linear-trend",
    "ctt": "constant + linear + quadratic-trend",
    "n":   "no-deterministic-term",
    "nc":  "no-deterministic-term",
}


def _tier2(results: dict) -> str:
    """Technical fragment: test statistics + specification disclosure.

    Mode-aware. In triage mode, all three tests appear plus the joint
    verdict label. In single-test mode, only ADF.

    §4.4 disclosure — regression specification always surfaces here, so
    the reader can audit whether the verdict would flip under a
    different deterministic term.
    """
    mode = results.get("mode", "single_test")
    regression = str(results.get("regression", "c"))
    reg_label = _REGRESSION_LABEL.get(regression, regression)
    used_lag = int(results.get("used_lag", 0))
    schwert = int(results.get("schwert_bound", 0))
    n_obs = int(results.get("n_obs", 0))

    adf_stat = float(results.get("adf_stat", 0.0))
    p_value = float(results.get("p_value", 1.0))
    crit_used = _critical_value_for_verdict(results)
    sig_level = float(results.get("significance_level", 0.05))
    sig_pct = f"{int(round(sig_level * 100))}%"

    pband = interpret_pvalue(p_value)
    adf_fragment = format_stat_technical(
        "ADF", adf_stat,
        critical_value=crit_used,
        p_value=p_value,
    )

    lag_phrase = _lag_phrase(used_lag)

    if mode == "triage":
        return _tier2_triage(
            results, regression, reg_label, n_obs, schwert, lag_phrase,
            adf_fragment, sig_pct,
        )

    # Single-test
    if pband["strength"] in ("strong", "standard", "marginal"):
        opener = (
            f"Augmented Dickey-Fuller {pband['phrase']} the unit-root null "
            f"at the {sig_pct} level ({adf_fragment})."
        )
        # Retroactive T9 fix: integrate the Schwert bound into a verb-
        # containing sentence rather than leaving it as a dangling
        # parenthetical disclosure.
        spec_sentence = (
            f"The test used a {reg_label} regression with {lag_phrase}, "
            f"with lag selection bounded by Schwert's rule ("
            f"{schwert} on {n_obs} observations)."
        )
        closer = (
            f"The regression='{regression}' specification is appropriate — "
            "the series shows no material linear trend."
            if (not bool(results.get("trending")) and regression == "c")
            else (
                f"Specification: regression='{regression}' ({reg_label})."
            )
        )
        return f"{opener} {spec_sentence} {closer}"

    # "does not reject" — Schwert bound integrated into the main sentence
    # so the disclosure carries a verb.
    return (
        f"Augmented Dickey-Fuller does not reject the unit-root null "
        f"({adf_fragment}, {reg_label} regression, {lag_phrase}, "
        f"with lag selection bounded by Schwert's rule at {schwert} on "
        f"{n_obs} observations). Consider first-differencing the series, "
        f"or re-running with a different regression specification."
    )


def _tier2_triage(
    results: dict,
    regression: str,
    reg_label: str,
    n_obs: int,
    schwert: int,
    lag_phrase: str,
    adf_fragment: str,
    sig_pct: str,
) -> str:
    """Triage-mode Tier 2: paragraph covering all three tests + verdict."""
    p_value = float(results.get("p_value", 1.0))
    kpss_stat = float(results.get("kpss_stat", 0.0))
    kpss_p = float(results.get("kpss_pvalue", 1.0))
    kpss_rej = bool(results.get("kpss_rejected"))
    pp_stat = float(results.get("pp_stat", 0.0))
    pp_p = float(results.get("pp_pvalue", 1.0))
    verdict = str(results.get("joint_verdict", "UNKNOWN"))

    adf_rej = bool(results.get("decision_rejected"))
    if adf_rej:
        adf_sentence = (
            f"Augmented Dickey-Fuller rejects the unit-root null at the "
            f"{sig_pct} level ({adf_fragment}, {reg_label} regression, "
            f"{lag_phrase})."
        )
    else:
        adf_sentence = (
            f"Augmented Dickey-Fuller does not reject the unit-root null "
            f"({adf_fragment}, {reg_label} regression, {lag_phrase})."
        )

    kpss_frag = format_stat_technical("KPSS", kpss_stat, p_value=kpss_p)
    if kpss_rej:
        kpss_sentence = (
            f"KPSS rejects the stationarity null at the {sig_pct} level "
            f"({kpss_frag})"
        )
    else:
        kpss_sentence = (
            f"KPSS does not reject the stationarity null ({kpss_frag})"
        )

    pp_frag = format_stat_technical("PP", pp_stat, p_value=pp_p)
    # PP has the same null as ADF, so agreement is measured on rejection.
    pp_agrees_adf = bool(results.get("pp_rejected")) == adf_rej
    pp_sentence = (
        f"Phillips-Perron {'agrees with' if pp_agrees_adf else 'disagrees with'} "
        f"ADF ({pp_frag})"
    )

    # Verdict-specific closer. CONFLICTING closes without the
    # follow-up sentence (moved to Tier 1 per Edit 6). Other verdicts
    # carry a short technical coda.
    if verdict == "CONFLICTING":
        coda = (
            "The usual causes are a one-time level shift, a trend break, a "
            "near-unit-root process (ρ close to 1), or a regime change "
            "mid-sample."
        )
    elif verdict == "STATIONARY":
        # Retroactive T8 fix: the prior coda ("series is usable directly in
        # stationarity-assuming models") restated the Tier 1 action. Replace
        # with a mechanistic statement of why the joint verdict is strong.
        coda = (
            "Both the ADF rejection and the KPSS non-rejection sit "
            "decisively on the correct sides of their critical values."
        )
    elif verdict == "UNIT ROOT (I(1))":
        coda = (
            "Confirm the first-differenced series passes this test before "
            "using it in level-based models."
        )
    elif verdict == "INCONCLUSIVE":
        coda = (
            "Both p-values sit above their rejection thresholds, typical of "
            "near-unit-root processes or small samples."
        )
    else:
        coda = ""

    # Integrate the Schwert-bound disclosure into the verdict sentence so
    # it isn't a dangling single-statistic fragment (retroactive T9 fix).
    verdict_sentence_with_bound = (
        f"The joint triage verdict is {verdict}; lag selection used "
        f"{lag_phrase} within a Schwert bound of {schwert} on "
        f"{n_obs} observations."
    )
    base = (
        f"{adf_sentence} {kpss_sentence}, and {pp_sentence}. "
        f"{verdict_sentence_with_bound}"
    )
    if coda:
        base = f"{base} {coda}"
    return base


def _critical_value_for_verdict(results: dict) -> Optional[float]:
    """Pick the critical value to cite alongside ADF in Tier 2.

    Default: the critical value at the user's significance level.
    Falls back to the 1% value if not supplied, then 5%. Returns None
    only if the caller provided neither — in that case
    :func:`format_stat_technical` renders only the statistic and
    p-value.
    """
    sig_level = float(results.get("significance_level", 0.05))
    if sig_level <= 0.01 and "crit_1pct" in results:
        return float(results["crit_1pct"])
    if "crit_5pct" in results:
        return float(results["crit_5pct"])
    if "crit_1pct" in results:
        return float(results["crit_1pct"])
    return None


def _lag_phrase(used_lag: int) -> str:
    """Grammar helper: phrase lag selection in English.

    Returns a noun phrase (no verb) so callers can embed it in a wider
    sentence without awkward "lag selection used X needed" constructions.
    """
    n = int(used_lag)
    if n == 0:
        return "no augmentation lags"
    if n == 1:
        return "one AIC-selected augmentation lag"
    return f"{n} AIC-selected augmentation lags"


# ---------------------------------------------------------------------
# Tier 3 — Conditional caveats
# ---------------------------------------------------------------------


def _trigger_trending_series(results: dict) -> Optional[str]:
    """Fires only when regression='c' AND |t_stat_trend| > 2.0.

    Edit 4: both conditions required so the caveat does not appear on
    runs where the user has already specified regression='ct'.
    """
    if results.get("regression") != "c":
        return None
    if not bool(results.get("trending")):
        return None
    t_stat = float(results.get("t_stat_trend", 0.0))
    if abs(t_stat) <= 2.0:
        return None
    return (
        f"The current run used regression='c' (constant only), but the "
        f"series shows a linear-time t-statistic of {t_stat:.1f} — this "
        "suggests a deterministic trend. Re-running with regression='ct' "
        "may change the verdict."
    )


def _trigger_borderline_p(results: dict) -> Optional[str]:
    """Fires when ADF p-value is within 0.01 of α=0.05 (i.e., in
    [0.04, 0.06]).

    Edit 7: direction-aware. If p<0.05, a stricter (1%) cutoff would
    fail to reject; if p>0.05, a looser (10%) cutoff would reject.
    """
    p = float(results.get("p_value", 1.0))
    if not (0.04 < p < 0.06):
        return None
    stricter_or_looser = "stricter (1%)" if p < 0.05 else "looser (10%)"
    return (
        f"The p-value ({p:.3f}) is close to the 5% threshold — the verdict "
        f"is sensitive to the chosen significance level and would change "
        f"under a {stricter_or_looser} cutoff."
    )


def _trigger_small_sample(results: dict) -> Optional[str]:
    """Fires when the sample is small relative to the mode.

    Single-test threshold: n < 50. Triage threshold: n < 100
    (three tests' worth of power budget is more demanding).
    """
    n_obs = int(results.get("n_obs", 0))
    mode = results.get("mode", "single_test")
    threshold = 100 if mode == "triage" else 50
    if n_obs >= threshold:
        return None
    return (
        f"Sample size is small (n={n_obs}); unit-root tests have limited "
        "power in this range. Treat the verdict as provisional."
    )


def _trigger_borderline_triage(results: dict) -> Optional[str]:
    """Fires in triage mode when BOTH ADF p and KPSS p are within 0.03 of α."""
    if results.get("mode") != "triage":
        return None
    alpha = float(results.get("significance_level", 0.05))
    adf_p = float(results.get("p_value", 1.0))
    kpss_p = float(results.get("kpss_pvalue", 1.0))
    if abs(adf_p - alpha) > 0.03 or abs(kpss_p - alpha) > 0.03:
        return None
    return (
        "Both tests are near their rejection thresholds; the joint "
        "verdict is marginal."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="adf_test",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_trending_series,
        _trigger_borderline_p,
        _trigger_small_sample,
        _trigger_borderline_triage,
    ),
    mode_aware=True,
)

register(SPEC)
