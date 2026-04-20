"""
InterpretationSpec for loess_interpolation.

Tier 1 leads with imputation count + LOESS fraction; per voice
revision V4, closer is actionable: validate longer-gap fills against
auxiliary data before relying on them.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    n_missing = int(results.get("n_missing", 0))
    pct = (100.0 * n_missing / n) if n > 0 else 0.0
    frac = float(results.get("frac", 0.0))
    n_gaps = int(results.get("n_gaps", 0))
    rmse = results.get("rmse")
    rmse_clause = (
        f"Fit RMSE on observed {FMT_COEF_UNSIGNED.format(float(rmse))}"
        if rmse is not None else "RMSE not reported"
    )
    return (
        f"{n_missing} of {n} observations ({pct:.0f}%) interpolated "
        f"in {format_series_reference(name)} using LOESS "
        f"(fraction={frac:.2f}) across {n_gaps} gap "
        f"segment{'s' if n_gaps != 1 else ''}. {rmse_clause}; short "
        f"gaps fill with high confidence. Validate longer-gap fills "
        f"against auxiliary data before relying on them — LOESS "
        f"inherits the global smoothness rather than quantifying per-"
        f"value uncertainty."
    )


def _tier2(results: dict) -> str:
    frac = float(results.get("frac", 0.0))
    it = int(results.get("it", 0))
    rmse = results.get("rmse")
    max_residual = results.get("max_residual")
    rmse_clause = (
        f"RMSE {FMT_COEF_UNSIGNED.format(float(rmse))}"
        if rmse is not None else "RMSE not reported"
    )
    maxr_clause = (
        f", max residual {FMT_COEF_UNSIGNED.format(float(max_residual))}"
        if max_residual is not None else ""
    )
    return (
        f"LOESS span {frac:.2f} with {it} robustifying iterations. "
        f"Unlike Kalman imputation, LOESS does not produce per-value "
        f"standard errors — uncertainty is assessed globally via "
        f"{rmse_clause}{maxr_clause} on observed data. LOESS is "
        f"deterministic given the span. For uncertainty-aware "
        f"imputation on longer gaps, prefer Kalman imputation."
    )


def _trigger_wide_span(results: dict) -> Optional[str]:
    frac = float(results.get("frac", 0.0))
    if frac <= 0.5:
        return None
    return (
        f"LOESS fraction {frac:.2f} exceeds 0.50 — the span is so "
        f"wide that LOESS degenerates toward a global polynomial fit, "
        f"smoothing over genuine local structure. Refit with a "
        f"narrower fraction (typically 0.1–0.3) and compare."
    )


def _trigger_long_gap(results: dict) -> Optional[str]:
    n = int(results.get("n_obs", 0))
    max_gap = int(results.get("max_gap", 0))
    if n == 0 or max_gap < 0.05 * n:
        return None
    return (
        f"Max gap length {max_gap} exceeds 5% of the series length. "
        f"Long gaps exceed the local-fit scale of LOESS and inherit "
        f"the surrounding smooth trend rather than any local detail. "
        f"Validate visually against auxiliary series or model fits "
        f"before relying on these imputations."
    )


SPEC = InterpretationSpec(
    technique_id="loess_interpolation",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_wide_span, _trigger_long_gap),
    mode_aware=False,
)

register(SPEC)
