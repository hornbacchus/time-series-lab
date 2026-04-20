"""
Shared stationarity-test tier renderer.

Internal helper (leading-underscore filename) used by the `kpss_test`
and `pp_test` interpretation specs. ADF's spec (`adf_test.py`) was
written earlier in Prompt A and handles both single-test and triage
modes with richer phrasing; it is not routed through this helper.
If ADF's phrasing ever needs to converge with KPSS/PP, the renderer
below can absorb the single-test ADF case too.

The critical distinction between the three stationarity tests is the
null-hypothesis direction:

  - ADF null = unit root   (reject → stationary)
  - KPSS null = stationarity (reject → non-stationary)
  - PP null = unit root    (reject → stationary)

The renderer is parameterized on ``null_direction`` to flip the
verdict language correctly.
"""

from typing import Optional

from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_STAT_DEFAULT,
    format_series_reference,
)


_REGRESSION_LABEL = {
    "c": "constant-only",
    "ct": "constant + linear trend",
    "ctt": "constant + quadratic trend",
    "n": "no-deterministic-term",
}


def _verdict_phrase(test_name: str, null_direction: str, rejected: bool) -> str:
    """Return the rejection / fail-to-reject verb phrase."""
    if rejected:
        return f"{test_name} rejects the {null_direction} null"
    return f"{test_name} fails to reject the {null_direction} null"


def _series_verdict_clause(null_direction: str, rejected: bool) -> str:
    """One-sentence interpretation: what does rejection/non-rejection imply
    about the series under this null direction?"""
    if null_direction == "unit_root" and rejected:
        return "The series is stationary — safe to apply stationarity-assuming models."
    if null_direction == "unit_root" and not rejected:
        return "Consistent with non-stationarity — difference before applying stationarity-assuming models."
    if null_direction == "stationarity" and rejected:
        return "The series carries persistent structure inconsistent with level-stationarity — difference before applying stationarity-assuming models."
    # null=stationarity, not rejected
    return "The series is consistent with level-stationarity — no evidence of persistent trend, safe to apply stationarity-assuming models."


def _triage_hint(null_direction: str, rejected: bool) -> str:
    """The complementary-test hint that appears in Tier 2.
    Pairs with the other two stationarity tests for a joint verdict."""
    if null_direction == "unit_root":
        # ADF / PP null = unit root. Complement is KPSS.
        if rejected:
            return (
                "Triple-test triage (ADF + KPSS + PP) strengthens the verdict: "
                "ADF/PP rejects AND KPSS fails-to-reject is the strongest "
                "evidence of stationarity."
            )
        return (
            "Pair with KPSS for a joint verdict: ADF/PP fails-to-reject AND "
            "KPSS rejects is the strongest evidence of non-stationarity."
        )
    # null = stationarity (KPSS)
    if rejected:
        return (
            "Pair with ADF for a joint verdict: KPSS rejects AND ADF "
            "fails-to-reject is the strongest evidence of non-stationarity."
        )
    return (
        "Failure to reject does not prove stationarity — pair with ADF "
        "(null = unit root) for a joint verdict: ADF rejects AND KPSS "
        "fails-to-reject is the strongest evidence of stationarity."
    )


def render_stationarity_tier(
    *,
    tier: int,
    test_name: str,
    null_direction: str,
    rejected: bool,
    series_name: str,
    stat_value: float,
    p_value: Optional[float],
    crit_value: float,
    significance: float,
    regression: str,
    sample_size: int,
    bandwidth: Optional[int] = None,
    trending: Optional[bool] = None,
    effective_sample_size: Optional[int] = None,
) -> str:
    """Render Tier 1 or Tier 2 text for a standalone KPSS / PP invocation.

    Parameters
    ----------
    tier
        1 or 2.
    test_name
        "KPSS" or "PP". Used verbatim in verdict phrasing.
    null_direction
        "stationarity" (KPSS) or "unit_root" (PP, ADF). Flips
        verdict-language direction.
    rejected
        Whether the null was rejected at ``significance``.
    stat_value, p_value, crit_value, significance
        Numeric values for Tier 2 citation; p_value may be None for
        PP variants that emit only critical-value comparisons.
    regression
        "c" / "ct" / "ctt" / "n" (pandas statsmodels convention).
    sample_size
        Observations used in the test.
    bandwidth
        Newey-West / HAC bandwidth (KPSS, PP). None when not applicable.
    trending
        If True AND regression == "c", Tier 2 suggests trying regression='ct'.
    effective_sample_size
        HAC-adjusted effective sample size, when the wrapper computes one.
        None when not applicable (most wrappers). Emitted in Tier 2 as
        context for the Newey-West bandwidth when present.
    """
    series_ref = format_series_reference(series_name)
    sig_pct = f"{int(round(significance * 100))}%"
    stat_str = FMT_STAT_DEFAULT.format(stat_value)
    crit_str = FMT_STAT_DEFAULT.format(crit_value)
    p_str = None
    if p_value is not None:
        p_str = f"p<0.001" if float(p_value) < 1e-3 else f"p={FMT_P_VALUE.format(float(p_value))}"

    verdict = _verdict_phrase(test_name, null_direction, rejected)

    if tier == 1:
        stat_display_name = "Z(t)" if test_name == "PP" else "LM"
        if p_str is not None and rejected:
            citation = f"{stat_display_name}={stat_str}, {p_str}"
        else:
            citation = (
                f"{stat_display_name}={stat_str}, critical value at {sig_pct}={crit_str}"
            )
        series_verdict = _series_verdict_clause(null_direction, rejected)
        newey_west_note = ""
        if test_name == "PP":
            newey_west_note = " PP's Newey-West correction handles heteroscedasticity without explicit lag augmentation."
        return (
            f"{verdict} for {series_ref} at the {sig_pct} level "
            f"({citation}). {series_verdict}{newey_west_note}"
        )

    # Tier 2
    reg_label = _REGRESSION_LABEL.get(regression, regression)
    bandwidth_clause = ""
    if bandwidth is not None:
        bandwidth_clause = f", Newey-West bandwidth {int(bandwidth)}"
        if effective_sample_size is not None:
            bandwidth_clause += f" (effective sample size {int(effective_sample_size)})"
    stat_line = f"{test_name} with regression='{regression}' ({reg_label}){bandwidth_clause} on {int(sample_size)} observations."
    if rejected:
        numeric_line = f"{stat_str} exceeds the {sig_pct} critical value {crit_str}."
        if test_name == "KPSS":
            numeric_line = f"LM statistic {stat_str} exceeds the {sig_pct} critical value {crit_str}."
        elif test_name == "PP":
            numeric_line = (
                f"Z(t)={stat_str} vs {sig_pct} critical {crit_str}."
            )
    else:
        if test_name == "KPSS":
            numeric_line = f"LM={stat_str} is below the {sig_pct} critical value {crit_str}."
        elif test_name == "PP":
            numeric_line = (
                f"Z(t)={stat_str} is above the {sig_pct} critical {crit_str}."
            )
        else:
            numeric_line = f"Statistic {stat_str} relative to {sig_pct} critical {crit_str}."

    if null_direction == "stationarity":
        null_clause = (
            "Null hypothesis is level-stationarity (NOT unit root); "
            "rejection means non-stationarity."
        )
    else:
        null_clause = "Null = unit root (mirrors ADF)."

    return f"{stat_line} {numeric_line} {null_clause} {_triage_hint(null_direction, rejected)}"
