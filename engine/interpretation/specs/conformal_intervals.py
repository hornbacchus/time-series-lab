"""
InterpretationSpec for conformal_intervals.

Per Decision B: verdict-free Tier 1. Baseline-comparison sentence
renders only when the wrapper provides `parametric_baseline_width`.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_PROBABILITY,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

# Preset-gated: parametric_baseline_width may be absent under some
# wrapper configurations (non-ARIMA base models, or presets that skip
# the baseline computation).
PRESET_GATED_KEYS = ("parametric_baseline_width",)


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    target_cov = float(results.get("target_coverage", 0.95))
    horizon = int(results.get("horizon", 0))
    avg_width = float(results.get("avg_interval_width", 0.0))
    parametric_width = results.get("parametric_baseline_width")
    cov_pct = int(round(target_cov * 100))
    # FIX 5: em-dash join rather than new sentence to avoid a fragment.
    baseline_clause = ""
    if parametric_width is not None and float(parametric_width) > 0:
        narrowness_pct = 100.0 * (1.0 - avg_width / float(parametric_width))
        if narrowness_pct > 0:
            baseline_clause = (
                f" — {narrowness_pct:.0f}% narrower than the parametric "
                f"baseline (width {format_scale_aware(float(parametric_width))})"
            )
        else:
            baseline_clause = (
                f" — {abs(narrowness_pct):.0f}% wider than the parametric "
                f"baseline (width {format_scale_aware(float(parametric_width))})"
            )
    return (
        f"Distribution-free {cov_pct}% prediction intervals for "
        f"{format_series_reference(name)} over a {horizon}-step "
        f"horizon. Average interval width "
        f"{format_scale_aware(avg_width)} (units match the "
        f"series){baseline_clause}. Conformal coverage is guaranteed "
        f"under exchangeability; validate via the calibration-"
        f"residual ACF in the data tables."
    )


def _tier2(results: dict) -> str:
    base_model = str(results.get("base_model", "ARIMA"))
    train_frac = results.get("train_frac")
    calib_frac = results.get("calibration_frac")
    conformal_q = results.get("conformal_quantile")
    split_clause = ""
    if train_frac is not None and calib_frac is not None:
        split_clause = (
            f", {int(float(train_frac) * 100)}/{int(float(calib_frac) * 100)} train/calibration split"
        )
    q_clause = (
        f"Conformal quantile {format_scale_aware(float(conformal_q))} "
        f"derived from the calibration residual distribution."
        if conformal_q is not None else
        "Conformal quantile computed from the calibration residual distribution."
    )
    return (
        f"Split-conformal prediction with {base_model} base model"
        f"{split_clause}. {q_clause} Unlike parametric intervals, "
        f"conformal coverage requires only exchangeability — no "
        f"distributional assumption. For time series, strict "
        f"exchangeability is violated by autocorrelation; the "
        f"residual-ACF diagnostic checks whether this violation is "
        f"material for the coverage guarantee."
    )


def _exchangeability_violated(results: dict) -> bool:
    ac1 = results.get("calibration_residual_acf_lag1")
    if ac1 is None:
        return False
    return abs(float(ac1)) > 0.3


def _no_tightness_gain(results: dict) -> bool:
    avg_width = results.get("avg_interval_width")
    baseline_width = results.get("parametric_baseline_width")
    if avg_width is None or baseline_width is None:
        return False
    return float(avg_width) >= float(baseline_width)


def _trigger_exchangeability_and_tightness_both_fail(results: dict) -> Optional[str]:
    """FIX 9: Combined trigger that pre-empts the two singles when both
    conditions hold. Renders the joint implication rather than two
    independent caveats read sequentially.
    """
    if not (_exchangeability_violated(results) and _no_tightness_gain(results)):
        return None
    ac1 = float(results.get("calibration_residual_acf_lag1"))
    avg_width = float(results.get("avg_interval_width"))
    baseline_width = float(results.get("parametric_baseline_width"))
    return (
        f"Calibration-residual lag-1 ACF {FMT_PROBABILITY.format(ac1)} "
        f"violates exchangeability while conformal width "
        f"{format_scale_aware(avg_width)} matches or exceeds the "
        f"parametric baseline {format_scale_aware(baseline_width)}. "
        f"Taken together: the base model is mis-specified AND the "
        f"conformal adjustment cannot recover tightness. Use the "
        f"intervals as rough upper bounds and reconsider the base "
        f"model."
    )


def _trigger_exchangeability_violated(results: dict) -> Optional[str]:
    if not _exchangeability_violated(results):
        return None
    # Suppress when the combined trigger will fire instead.
    if _no_tightness_gain(results):
        return None
    ac1 = results.get("calibration_residual_acf_lag1")
    return (
        f"Calibration-residual lag-1 ACF "
        f"{FMT_PROBABILITY.format(float(ac1))} exceeds 0.3; "
        f"exchangeability is substantially violated. Nominal "
        f"coverage overstates true coverage on this series — treat "
        f"the intervals as approximate rather than guaranteed."
    )


def _trigger_no_tightness_gain(results: dict) -> Optional[str]:
    if not _no_tightness_gain(results):
        return None
    # Suppress when the combined trigger will fire instead.
    if _exchangeability_violated(results):
        return None
    avg_width = results.get("avg_interval_width")
    baseline_width = results.get("parametric_baseline_width")
    return (
        f"Conformal interval width "
        f"{format_scale_aware(float(avg_width))} is at or above "
        f"the parametric baseline width "
        f"{format_scale_aware(float(baseline_width))} — "
        f"conformal adds no tightness. Verify the base model is "
        f"adequate; the conformal adjustment is protecting against "
        f"severe parametric mis-calibration."
    )


SPEC = InterpretationSpec(
    technique_id="conformal_intervals",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # Combined trigger first — it suppresses the two singles
        # when both conditions hold.
        _trigger_exchangeability_and_tightness_both_fail,
        _trigger_exchangeability_violated,
        _trigger_no_tightness_gain,
    ),
    mode_aware=False,
)

register(SPEC)
