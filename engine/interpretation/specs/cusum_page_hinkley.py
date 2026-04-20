"""
InterpretationSpec for cusum_page_hinkley.

Tier 1 names the two parallel detectors and reports alarms by method
and direction. Agreement across methods is the signal-strength proxy.
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
    total_alarms = int(results.get("n_alarms_total", 0))
    n_up = int(results.get("n_alarms_upward", 0))
    n_down = int(results.get("n_alarms_downward", 0))
    most_recent = results.get("most_recent_alarm_date")
    shift_pre = results.get("most_recent_pre_mean")
    shift_post = results.get("most_recent_post_mean")
    agreement = results.get("most_recent_method_agreement")
    if total_alarms == 0:
        return (
            f"CUSUM + Page-Hinkley raised no level-shift alarms across "
            f"two parallel detectors on {format_series_reference(name)} "
            f"({n_obs} observations). No structural breaks detected "
            f"under the current threshold configuration."
        )
    detail = ""
    if most_recent and shift_pre is not None and shift_post is not None:
        detail = (
            f"; most recent at {most_recent} with pre/post mean shift "
            f"{float(shift_pre):.2f} → {float(shift_post):.2f}"
        )
    agreement_clause = ""
    if agreement:
        agreement_clause = (
            " Dual-method agreement on the most recent alarm — both "
            "CUSUM and PH fired — is the strongest signal."
        )
    return (
        f"CUSUM + Page-Hinkley raised {total_alarms} level-shift "
        f"alarm{'s' if total_alarms != 1 else ''} across two parallel "
        f"detectors on {format_series_reference(name)} ({n_obs} "
        f"observations). {n_up} upward and {n_down} downward{detail}."
        f"{agreement_clause}"
    )


def _tier2(results: dict) -> str:
    cusum_h = results.get("cusum_threshold")
    ph_delta = results.get("ph_delta")
    ph_lambda = results.get("ph_lambda")
    cusum_clause = (
        f"CUSUM with threshold h={cusum_h}" if cusum_h is not None
        else "CUSUM with preset-default threshold"
    )
    ph_clause = (
        f"Page-Hinkley with δ={ph_delta} and λ={ph_lambda}"
        if (ph_delta is not None and ph_lambda is not None)
        else "Page-Hinkley with preset-default parameters"
    )
    return (
        f"Two parallel detectors: {cusum_clause}, and {ph_clause}. "
        f"Alarms enumerated by method and direction. Agreement between "
        f"methods on a given date increases confidence; lone-method "
        f"alarms warrant visual verification. Both are online — they "
        f"do not retrospectively re-estimate change-point positions "
        f"as BOCPD or PELT do."
    )


def _trigger_method_disagreement(results: dict) -> Optional[str]:
    n_cusum = int(results.get("n_alarms_cusum", 0))
    n_ph = int(results.get("n_alarms_page_hinkley", 0))
    if n_cusum == 0 or n_ph == 0:
        return None
    ratio = max(n_cusum, n_ph) / min(n_cusum, n_ph)
    if ratio <= 2.0:
        return None
    return (
        f"CUSUM ({n_cusum}) and Page-Hinkley ({n_ph}) alarm counts "
        f"differ by more than 2×. The methods disagree substantially; "
        f"either the series violates within-segment stationarity "
        f"(both detectors' assumption) or the thresholds need "
        f"retuning for comparable sensitivity."
    )


def _trigger_alarm_cluster(results: dict) -> Optional[str]:
    cluster_max = results.get("max_alarms_in_segment")
    if cluster_max is None:
        return None
    if int(cluster_max) <= 3:
        return None
    return (
        f"A single segment contains {int(cluster_max)} alarms — the "
        f"thresholds are hypersensitive relative to the series "
        f"dynamics. Raise the CUSUM threshold h or the Page-Hinkley λ "
        f"and re-run to reduce alarm clustering."
    )


SPEC = InterpretationSpec(
    technique_id="cusum_page_hinkley",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_method_disagreement, _trigger_alarm_cluster),
    mode_aware=False,
)

register(SPEC)
