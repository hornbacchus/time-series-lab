"""
InterpretationSpec for pelt_change_points.

Tier 1 names PELT as the offline penalized-optimum framework and
reports the count of change points under the chosen cost + penalty.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n_obs = int(results.get("n_obs", 0))
    n_cp = int(results.get("n_change_points", 0))
    cost_model = str(results.get("cost_model", "L2"))
    penalty = results.get("penalty")
    most_recent = results.get("most_recent_cp_date")
    pre = results.get("most_recent_pre_mean")
    post = results.get("most_recent_post_mean")
    penalty_clause = f"penalty {float(penalty):.1f}" if penalty is not None else "preset-default penalty"
    if n_cp == 0:
        return (
            f"PELT identified no change points as the offline penalized "
            f"optimum for {format_series_reference(name)} ({n_obs} "
            f"observations) under the {cost_model} cost and "
            f"{penalty_clause}. The series is best explained as a "
            f"single segment under this configuration; lowering the "
            f"penalty increases sensitivity at the cost of more false "
            f"positives."
        )
    shift_clause = ""
    if most_recent and pre is not None and post is not None:
        shift_clause = (
            f" Most recent at {most_recent} with pre/post mean shift "
            f"{float(pre):.2f} → {float(post):.2f}."
        )
    return (
        f"PELT identified {n_cp} change point{'s' if n_cp != 1 else ''} "
        f"as the offline penalized optimum for "
        f"{format_series_reference(name)} ({n_obs} observations) under "
        f"the {cost_model} cost and {penalty_clause}.{shift_clause} "
        f"Segments enumerated in the data tables."
    )


def _tier2(results: dict) -> str:
    cost_model = str(results.get("cost_model", "L2"))
    penalty = results.get("penalty")
    penalty_clause = f"penalty {float(penalty):.1f}" if penalty is not None else "preset-default penalty"
    return (
        f"Pruned exact linear-time segmentation with {cost_model} cost "
        f"function and {penalty_clause}. Unlike BOCPD, PELT is an "
        f"offline optimum — the change points minimize a penalized "
        f"sum-of-cost-function-terms over the full series. Lower "
        f"penalty produces more change points; higher penalty fewer. "
        f"The penalty reflects a preset-dependent trade-off between "
        f"detection sensitivity and false-positive rate."
    )


def _trigger_low_count_on_long_series(results: dict) -> Optional[str]:
    n_obs = int(results.get("n_obs", 0))
    n_cp = int(results.get("n_change_points", 0))
    if n_obs <= 500 or n_cp >= 2:
        return None
    return (
        f"Only {n_cp} change point{'s' if n_cp != 1 else ''} detected "
        f"on {n_obs} observations. The penalty may be too high; "
        f"lowering it reveals subtler transitions at the cost of "
        f"admitting more false positives."
    )


def _trigger_dominant_segment(results: dict) -> Optional[str]:
    n_obs = int(results.get("n_obs", 0))
    largest_segment = results.get("largest_segment_size")
    if largest_segment is None or n_obs == 0:
        return None
    if int(largest_segment) <= 0.5 * n_obs:
        return None
    return (
        f"One dominant segment accounts for more than 50% of the "
        f"observations ({int(largest_segment)} of {n_obs}). Verify "
        f"model fit within that segment; global properties of PELT "
        f"don't exclude within-segment heterogeneity."
    )


SPEC = InterpretationSpec(
    technique_id="pelt_change_points",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_low_count_on_long_series, _trigger_dominant_segment),
    mode_aware=False,
)

register(SPEC)
