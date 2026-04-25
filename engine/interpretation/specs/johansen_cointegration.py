"""
InterpretationSpec for johansen_cointegration.

NEW Tier 1 shape — rank-centric (multivariate rank test, parallels ADF/
KPSS/PP but outputs rank + β). Tier 1 leads with trace-test-selects-rank
phrasing and cites the rank-implication actionable clause (Decision D7):

    rank=0        → differenced-VAR is recommended
    1 ≤ r < k-1   → VECM with r long-run equilibrium relationships
    r ≥ k-1       → levels-VAR may be appropriate

Decision D8: MacKinnon-Haug-Michelis asymptotic small-sample caveat in
Tier 2 — honest disclosure that CVs over-reject on n < 100.

Follow-up 3d: opt-in `finite_sample_correction=True` applies Reimers
(1992) modified likelihood-ratio correction (a Bartlett-type factor;
R urca ``ca.jo(small_sample=TRUE)`` / Stata vecrank standard). Tier 1
gains a closer when the correction flips rank inference. Tier 2 gains
a methodology block when correction is applied, plus a fallback block
on graceful degradation. Existing `_trigger_small_sample` (D8, C5) is
re-gated to suppress when the user opts in, and its text is updated
to point at `finite_sample_correction=True` as the actionable option
when firing on the opt-out path. Four new Tier 3 triggers (D1–D4)
cover the rank-flip, material-no-flip, very-small-sample, and
runtime-error cases.

Results-dict keys consumed:

    variable_names / n_variables
    lag_order / det_order
    trace_rank / max_eig_rank
    trace_stat_at_decision / trace_cv_at_decision
    significance_level
    eigenvalues / first_cointegrating_vector
    rank_implication_label
    n_observations
    tests_agree
    # Follow-up 3d
    finite_sample_correction_requested / finite_sample_correction_applied
    finite_sample_correction_fallback_reason / correction_method
    bartlett_factor / correction_pct_reduction
    trace_stat_corrected / trace_rank_corrected
    max_eig_stat_corrected / max_eig_rank_corrected
    correction_impact_material
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    FMT_COEF_SIGNED,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _rank_implication_sentence(label: str, r: int, k: int) -> str:
    lbl = str(label or "").lower()
    if lbl == "differenced-var" or r == 0:
        return (
            "The rank indicates no long-run equilibrium — a VAR model in "
            "first differences is the recommended downstream specification."
        )
    if lbl == "levels-var" or r >= k - 1:
        return (
            f"The rank {r} approaches the number of variables ({k}); the "
            f"series may all be stationary, so a VAR in levels is "
            f"appropriate. Verify with per-series stationarity triage before "
            f"committing."
        )
    return (
        f"The rank indicates {r} long-run equilibrium "
        f"relationship{'s' if r != 1 else ''} among the {k} series — a "
        f"VECM (Vector Error Correction Model) is the recommended "
        f"downstream specification, not a differenced VAR."
    )


def _tier1(results: dict) -> str:
    names = list(results.get("variable_names") or [])
    k = int(results.get("n_variables", len(names)))
    p = int(results.get("lag_order", 0))
    r = int(results.get("trace_rank", 0))
    max_eig_r = int(results.get("max_eig_rank", r))
    stat = results.get("trace_stat_at_decision")
    cv = results.get("trace_cv_at_decision")
    sig = str(results.get("significance_level", "5%"))
    tests_agree = bool(results.get("tests_agree", True))
    label = str(results.get("rank_implication_label", "VECM"))

    names_quoted = ", ".join(f"'{n}'" for n in names) if names else f"{k} series"

    stat_str = format_scale_aware(float(stat)) if stat is not None else "unavailable"
    cv_str = format_scale_aware(float(cv)) if cv is not None else "unavailable"

    agreement_clause = ""
    if tests_agree:
        agreement_clause = f" Max-eigenvalue test agrees (rank {max_eig_r})."
    else:
        agreement_clause = (
            f" Max-eigenvalue test disagrees (rank {max_eig_r}); the "
            f"trace-test decision is cited per the robustness convention."
        )

    implication = _rank_implication_sentence(label, r, k)

    base_tier1 = (
        f"Johansen cointegration test on {k} series ({names_quoted}) at "
        f"VAR lag {p}: **trace test selects rank {r}** (trace statistic "
        f"{stat_str} vs {sig} critical value {cv_str}).{agreement_clause} "
        f"{implication}"
    )

    # Follow-up 3d: append a closer when finite-sample correction was
    # applied AND it changed the rank inference (the critical
    # practitioner signal). Non-material corrections don't clutter
    # Tier 1.
    if (
        bool(results.get("finite_sample_correction_applied", False))
        and bool(results.get("correction_impact_material", False))
    ):
        try:
            T = int(results.get("n_observations", 0))
            tr_rank_u = int(results.get("trace_rank", 0))
            tr_rank_c = int(
                results.get("trace_rank_corrected", tr_rank_u)
            )
            me_rank_u = int(results.get("max_eig_rank", 0))
            me_rank_c = int(
                results.get("max_eig_rank_corrected", me_rank_u)
            )
            pct = float(results.get("correction_pct_reduction") or 0.0)
            flips = []
            if tr_rank_u != tr_rank_c:
                flips.append(f"trace r = {tr_rank_u} → {tr_rank_c}")
            if me_rank_u != me_rank_c:
                flips.append(
                    f"max-eigenvalue r = {me_rank_u} → {me_rank_c}"
                )
            flip_desc = "; ".join(flips) if flips else "rank inference"
            base_tier1 = base_tier1 + (
                f" Reimers (1992) finite-sample correction reduces "
                f"test statistics by {pct:.1%}, changing {flip_desc}. "
                f"With T = {T} observations the asymptotic test "
                f"over-rejects; the corrected rank is the reliable "
                f"estimate."
            )
        except Exception:
            pass

    return base_tier1


def _tier2(results: dict) -> str:
    k = int(results.get("n_variables", 0))
    p = int(results.get("lag_order", 0))
    det = int(results.get("det_order", 0) or 0)
    r_trace = int(results.get("trace_rank", 0))
    r_maxeig = int(results.get("max_eig_rank", r_trace))
    sig = str(results.get("significance_level", "5%"))
    stat = results.get("trace_stat_at_decision")
    cv = results.get("trace_cv_at_decision")
    eigs = list(results.get("eigenvalues") or [])
    beta = results.get("first_cointegrating_vector")
    n = int(results.get("n_observations", 0))
    names = list(results.get("variable_names") or [])

    stat_str = format_scale_aware(float(stat)) if stat is not None else "unavailable"
    cv_str = format_scale_aware(float(cv)) if cv is not None else "unavailable"

    # Eigenvalues rendering
    if eigs:
        eig_str = "{" + ", ".join(
            format_scale_aware(float(e)) for e in eigs
        ) + "}"
    else:
        eig_str = "not reported"

    # Cointegrating vector rendering (only when rank >= 1)
    if beta and r_trace >= 1:
        beta_parts = []
        for i, b in enumerate(beta):
            try:
                beta_parts.append(FMT_COEF_SIGNED.format(float(b)))
            except Exception:
                continue
        beta_str = "{" + ", ".join(beta_parts) + "}"
        if names and len(names) == len(beta):
            vars_tuple = "(" + ", ".join(names) + ")"
            beta_sent = (
                f" First cointegrating vector {beta_str} on {vars_tuple}."
            )
        else:
            beta_sent = f" First cointegrating vector {beta_str}."
    else:
        beta_sent = ""

    # Follow-up 3d: re-gate Decision D8 (MacKinnon small-sample caveat).
    # Suppress when the user opted in via finite_sample_correction=True
    # (the dedicated correction-methodology block below replaces it).
    # Update text when firing on the opt-out path to point at the new
    # actionable parameter.
    correction_requested = bool(
        results.get("finite_sample_correction_requested", False)
    )
    correction_applied = bool(
        results.get("finite_sample_correction_applied", False)
    )

    small_sample_clause = ""
    if not correction_requested:
        small_sample_clause = (
            f" Critical values use MacKinnon (1996) asymptotic tables "
            f"via statsmodels; on samples below ~100 observations these "
            f"over-reject the no-cointegration null. Set "
            f"finite_sample_correction=True to apply the Reimers (1992) "
            f"Bartlett-type correction to the test statistics "
            f"(R urca / Stata vecrank standard; see also Johansen 2002 "
            f"for higher-order refinements)."
        )
        if n >= 100:
            small_sample_clause += (
                f" This {n}-observation series is well above that "
                f"threshold so asymptotic inference is reliable."
            )

    # Follow-up 3d: correction methodology block when applied.
    corr_clause = ""
    if correction_applied:
        try:
            B = results.get("bartlett_factor")
            pct = results.get("correction_pct_reduction")
            tr_u = int(results.get("trace_rank", 0))
            tr_c = int(results.get("trace_rank_corrected", tr_u))
            me_u = int(results.get("max_eig_rank", 0))
            me_c = int(results.get("max_eig_rank_corrected", me_u))
            rank_result_clause = ""
            if tr_u != tr_c or me_u != me_c:
                rank_result_clause = (
                    f" Rank inference: uncorrected trace r = {tr_u}, "
                    f"corrected trace r = {tr_c}; uncorrected "
                    f"max-eigenvalue r = {me_u}, corrected r = {me_c}."
                )
            else:
                rank_result_clause = (
                    f" Rank inference is stable under correction "
                    f"(trace r = {tr_c}, max-eigenvalue r = {me_c})."
                )
            B_str = (
                f"{float(B):.4f}" if B is not None else "n/a"
            )
            pct_str = (
                f"{float(pct):.1%}" if pct is not None else "n/a"
            )
            corr_clause = (
                f" Finite-sample correction: Reimers (1992) modified "
                f"likelihood-ratio factor B = (T − n·p − d)/T = "
                f"{B_str} (reduction {pct_str}) applied to both trace "
                f"and maximum-eigenvalue statistics. This is the "
                f"Bartlett-type correction implemented as the R urca "
                f"package's small-sample option (small_sample = TRUE "
                f"in older urca versions; the factor is now applied "
                f"manually by extracting urca's raw statistics) and "
                f"as Stata vecrank's default. The Phase 1 reference-"
                f"parity audit (3d) verified bitwise equivalence of "
                f"the (T − n·p − d)/T arithmetic against R urca's "
                f"small-sample factor. Corrected statistics are "
                f"compared against the statsmodels asymptotic "
                f"critical-value tables (Osterwald-Lenum 1992 "
                f"convention, the statsmodels-internal default); "
                f"these are arithmetically equivalent to MHM 1999 "
                f"response-surface CVs at the decision level. "
                f"Johansen 2002 provides refined higher-order terms "
                f"not implemented here."
                + rank_result_clause
            )
        except Exception:
            corr_clause = ""

    # Follow-up 3d: fallback disclosure when requested but not applied.
    fallback_clause = ""
    if correction_requested and not correction_applied:
        reason = str(
            results.get("finite_sample_correction_fallback_reason") or ""
        )
        if reason.startswith("runtime_error"):
            fallback_clause = (
                f" Finite-sample correction was requested but raised an "
                f"unexpected runtime error ({reason}). Reverted to "
                f"uncorrected asymptotic inference."
            )
        elif reason:
            fallback_clause = (
                f" Finite-sample correction was requested but could not "
                f"be applied ({reason}). Reverted to uncorrected "
                f"asymptotic inference."
            )

    agreement = (
        "Max-eigenvalue agrees."
        if r_trace == r_maxeig else
        f"Max-eigenvalue disagrees (selects rank {r_maxeig}); prefer the "
        f"trace test's decision of rank {r_trace} for robustness."
    )

    return (
        f"Johansen trace and maximum-eigenvalue tests for cointegration "
        f"rank, estimated via VAR({p}) in levels with "
        f"{'no deterministic component' if det == 0 else f'deterministic order {det}'} "
        f"(det_order={det}). Trace statistic at the decision boundary: "
        f"{stat_str} vs {sig} critical value {cv_str}. {agreement} "
        f"Eigenvalues {eig_str}.{beta_sent}{small_sample_clause}"
        f"{corr_clause}{fallback_clause}"
    )


def _trigger_tests_disagree(results: dict) -> Optional[str]:
    if bool(results.get("tests_agree", True)):
        return None
    r_trace = int(results.get("trace_rank", 0))
    r_maxeig = int(results.get("max_eig_rank", 0))
    return (
        f"Trace test selects rank {r_trace} but max-eigenvalue test selects "
        f"rank {r_maxeig}. The two tests disagree; this is a borderline "
        f"case where the cointegration verdict is sensitive to test choice. "
        f"The trace test is typically preferred for robustness, but consider "
        f"running a sensitivity analysis over the lag order or widening the "
        f"significance level."
    )


def _trigger_small_sample(results: dict) -> Optional[str]:
    """D8 (legacy, C5) — fires only on the
    finite_sample_correction=False path. Text now points at the
    actionable finite_sample_correction=True option (Follow-up 3d)."""
    # Suppressed when the user has opted in — the dedicated Tier 2
    # methodology block and the Finite-Sample Correction output table
    # already deliver the message.
    if bool(results.get("finite_sample_correction_requested", False)):
        return None
    n = int(results.get("n_observations", 0))
    if n >= 100:
        return None
    return (
        f"Sample size n={n} is below 100 observations. MacKinnon "
        f"asymptotic critical values over-reject the no-cointegration "
        f"null on small samples; the rank decision may be inflated. "
        f"Set finite_sample_correction=True to apply the Reimers "
        f"(1992) Bartlett-type correction — the wrapper will compute "
        f"the Bartlett factor, report both uncorrected and corrected "
        f"statistics, and flag any rank inference that changes. "
        f"Reinsel-Ahn and Cheung-Lai are alternative corrections not "
        f"implemented here."
    )


def _trigger_rank_at_boundary(results: dict) -> Optional[str]:
    r = int(results.get("trace_rank", 0))
    k = int(results.get("n_variables", 0))
    if k <= 1 or r < k - 1 or r > k:
        return None
    if r == 0:
        return None
    return (
        f"Trace rank {r} at or above k-1={k-1}; the series may all be "
        f"stationary, in which case a VAR in levels is appropriate and the "
        f"cointegration framing adds no value. Verify with per-series "
        f"stationarity tests (ADF, KPSS, PP) before committing to a VECM."
    )


# ── Follow-up 3d Tier 3 triggers (D1-D4) ───────────────────────────


def _trigger_correction_flips_rank_conclusion(
    results: dict,
) -> Optional[str]:
    """D1 (3d) — fires when finite-sample correction flips rank
    inference for either test."""
    if not bool(
        results.get("finite_sample_correction_applied", False)
    ):
        return None
    if not bool(results.get("correction_impact_material", False)):
        return None
    try:
        tr_u = int(results.get("trace_rank", 0))
        tr_c = int(results.get("trace_rank_corrected", tr_u))
        me_u = int(results.get("max_eig_rank", 0))
        me_c = int(results.get("max_eig_rank_corrected", me_u))
        T = int(results.get("n_observations", 0))
        pct = float(results.get("correction_pct_reduction") or 0.0)
    except Exception:
        return None
    flips = []
    if tr_u != tr_c:
        flips.append(f"trace r = {tr_u} → {tr_c}")
    if me_u != me_c:
        flips.append(f"max-eigenvalue r = {me_u} → {me_c}")
    flip_desc = "; ".join(flips) if flips else "rank inference"
    return (
        f"Bartlett finite-sample correction changes rank inference "
        f"({flip_desc}). With T = {T} observations the asymptotic "
        f"MacKinnon critical values over-reject the no-cointegration "
        f"null; the {pct:.1%} statistic reduction under Reimers (1992) "
        f"is material. The corrected rank is the reliable estimate — "
        f"use it for downstream VECM / VAR specification decisions."
    )


def _trigger_correction_material_no_flip(
    results: dict,
) -> Optional[str]:
    """D2 (3d) — fires when correction is material (>5% reduction)
    but rank inference is stable. Q4: suppress when |1-factor| < 1%."""
    if not bool(
        results.get("finite_sample_correction_applied", False)
    ):
        return None
    if bool(results.get("correction_impact_material", False)):
        return None  # D1 covers the flip case
    try:
        pct = float(results.get("correction_pct_reduction") or 0.0)
    except Exception:
        return None
    # Q4: suppress when correction is below 1% (immaterial short-circuit)
    if pct < 0.01:
        return None
    # Fire only when correction is >= 5% (D2 threshold)
    if pct < 0.05:
        return None
    try:
        T = int(results.get("n_observations", 0))
        tr_c = int(
            results.get(
                "trace_rank_corrected",
                results.get("trace_rank", 0),
            )
        )
        me_c = int(
            results.get(
                "max_eig_rank_corrected",
                results.get("max_eig_rank", 0),
            )
        )
    except Exception:
        return None
    return (
        f"Reimers (1992) Bartlett-type correction reduces test "
        f"statistics by {pct:.1%}, but rank inference is stable "
        f"(corrected trace r = {tr_c}, corrected max-eigenvalue "
        f"r = {me_c}). Small-sample size distortion at T = {T} would "
        f"have been material; the corrected rank is the reliable "
        f"estimate."
    )


def _trigger_sample_size_below_threshold(
    results: dict,
) -> Optional[str]:
    """D3 (3d) — fires when T < 50 with correction applied. Bartlett
    correction is asymptotic in T; residual size distortion is plausible
    for very small samples."""
    if not bool(
        results.get("finite_sample_correction_applied", False)
    ):
        return None
    try:
        T = int(results.get("n_observations", 0))
    except Exception:
        return None
    if T >= 50:
        return None
    return (
        f"Sample T = {T} is very small. The Reimers Bartlett-type "
        f"correction is asymptotic in T and may leave residual size "
        f"distortion below T = 50. For more reliable rank inference "
        f"at this sample size, consider bootstrap-based methods "
        f"(Cavaliere-Rahbek-Taylor 2012) or Reinsel-Ahn / Cheung-Lai "
        f"corrections, which are not implemented in this wrapper."
    )


def _trigger_finite_sample_correction_runtime_error(
    results: dict,
) -> Optional[str]:
    """D4 (3d) — fires when correction requested but runtime error
    forced graceful fallback."""
    if not bool(
        results.get("finite_sample_correction_requested", False)
    ):
        return None
    if bool(results.get("finite_sample_correction_applied", False)):
        return None
    reason = str(
        results.get("finite_sample_correction_fallback_reason") or ""
    )
    if not reason.startswith("runtime_error"):
        return None
    return (
        f"Finite-sample correction was requested but raised an "
        f"unexpected runtime error ({reason}). Reverted to uncorrected "
        f"asymptotic inference. Please report a reproducible example; "
        f"the baseline Johansen output is the uncorrected fit."
    )


SPEC = InterpretationSpec(
    technique_id="johansen_cointegration",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # C5 legacy triggers
        _trigger_tests_disagree,
        _trigger_small_sample,  # re-gated (3d)
        _trigger_rank_at_boundary,
        # Follow-up 3d D1-D4
        _trigger_correction_flips_rank_conclusion,
        _trigger_correction_material_no_flip,
        _trigger_sample_size_below_threshold,
        _trigger_finite_sample_correction_runtime_error,
    ),
    mode_aware=False,
)

register(SPEC)
