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

    return (
        f"Johansen cointegration test on {k} series ({names_quoted}) at "
        f"VAR lag {p}: **trace test selects rank {r}** (trace statistic "
        f"{stat_str} vs {sig} critical value {cv_str}).{agreement_clause} "
        f"{implication}"
    )


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

    # Decision D8 — MacKinnon-Haug-Michelis small-sample caveat
    small_sample_clause = (
        f" Critical values use MacKinnon-Haug-Michelis asymptotic distributions; "
        f"on samples below ~100 observations these tend to over-reject the "
        f"no-cointegration null. Treat marginal rejections cautiously and "
        f"consider finite-sample-corrected alternatives if the sample is small."
    )
    if n >= 100:
        small_sample_clause += (
            f" This {n}-observation series is well above that threshold so "
            f"asymptotic inference is reliable."
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
    n = int(results.get("n_observations", 0))
    if n >= 100:
        return None
    return (
        f"Sample size n={n} is below 100 observations. MacKinnon-Haug-"
        f"Michelis asymptotic critical values over-reject the no-"
        f"cointegration null on small samples; the rank decision may be "
        f"inflated. Consider Reinsel-Ahn or Cheung-Lai finite-sample "
        f"corrections (not applied by this wrapper) or obtain more data."
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


SPEC = InterpretationSpec(
    technique_id="johansen_cointegration",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_tests_disagree,
        _trigger_small_sample,
        _trigger_rank_at_boundary,
    ),
    mode_aware=False,
)

register(SPEC)
