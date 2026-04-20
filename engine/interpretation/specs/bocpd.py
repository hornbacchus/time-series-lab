"""
InterpretationSpec for bocpd.

Tier 1 names the BOCPD framework explicitly and reports the count of
posterior-probability-thresholded change points. Tier 2 explains the
run-length posterior and the threshold-vs-detection trade-off.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_PROBABILITY,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n_obs = int(results.get("n_obs", 0))
    n_cps = int(results.get("n_cps", 0))
    most_recent = results.get("most_recent_cp_date")
    most_recent_prob = results.get("most_recent_cp_prob")
    most_recent_pre = results.get("most_recent_pre_mean")
    most_recent_post = results.get("most_recent_post_mean")
    if n_cps == 0:
        return (
            f"BOCPD detected no posterior-probability-thresholded change "
            f"points in {format_series_reference(name)} ({n_obs} "
            f"observations). The run-length posterior never crossed the "
            f"configured threshold; the series is consistent with a "
            f"single regime under the chosen hazard rate."
        )
    detail = ""
    if most_recent and most_recent_prob is not None:
        prob_str = FMT_PROBABILITY.format(float(most_recent_prob))
        shift_str = ""
        if most_recent_pre is not None and most_recent_post is not None:
            shift_str = f" and mean shift {float(most_recent_pre):.2f} → {float(most_recent_post):.2f}"
        detail = (
            f" Most recent at {most_recent} with posterior probability "
            f"{prob_str}{shift_str}."
        )
    return (
        f"BOCPD detected {n_cps} posterior-probability-thresholded "
        f"change point{'s' if n_cps != 1 else ''} in "
        f"{format_series_reference(name)} ({n_obs} observations)."
        f"{detail} Regime boundaries from the run-length posterior "
        f"appear in the data tables; inspect the full probability "
        f"path for finer structure."
    )


def _tier2(results: dict) -> str:
    hazard = results.get("hazard_rate")
    threshold = results.get("probability_threshold")
    hazard_clause = (
        f"hazard rate {float(hazard)}" if hazard is not None
        else "default hazard rate"
    )
    thresh_clause = (
        f"P ≥ {float(threshold)}" if threshold is not None
        else "the configured threshold"
    )
    return (
        f"Bayesian online change-point detection with {hazard_clause}. "
        f"Run-length posterior thresholded at {thresh_clause} to "
        f"enumerate the change points. Each detection cites the "
        f"posterior probability at detection time and the pre/post "
        f"segment means. Unlike offline PELT, BOCPD is streaming-"
        f"compatible — useful for real-time monitoring once enough "
        f"history accumulates."
    )


def _trigger_trailing_detection(results: dict) -> Optional[str]:
    n_obs = int(results.get("n_obs", 0))
    most_recent_idx = results.get("most_recent_cp_index")
    if most_recent_idx is None or n_obs <= 0:
        return None
    distance = n_obs - int(most_recent_idx)
    if distance > 5:
        return None
    return (
        f"Most recent change point is within {distance} observation"
        f"{'s' if distance != 1 else ''} of the series end. Trailing "
        f"detections are uncertain; more data may reverse the call, "
        f"and real-time users should treat recent change points as "
        f"provisional."
    )


def _trigger_high_detection_count(results: dict) -> Optional[str]:
    n_obs = int(results.get("n_obs", 0))
    n_cps = int(results.get("n_cps", 0))
    if n_obs == 0 or n_cps <= 0.1 * n_obs:
        return None
    return (
        f"Detection count {n_cps} exceeds 10% of the series length. "
        f"The posterior-probability threshold may be too loose; "
        f"raising it reduces false positives at the cost of missing "
        f"subtler transitions."
    )


SPEC = InterpretationSpec(
    technique_id="bocpd",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_trailing_detection, _trigger_high_detection_count),
    mode_aware=False,
)

register(SPEC)
