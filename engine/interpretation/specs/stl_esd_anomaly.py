"""
InterpretationSpec for stl_esd_anomaly.

Tier 1 names the seasonal-ESD test and reports count + rate + alpha
+ direction split. Tier 2 explains the STL-remainder pre-processing.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n_obs = int(results.get("n_obs", 0))
    n_anom = int(results.get("n_anomalies", 0))
    alpha = float(results.get("alpha", 0.05))
    n_up = int(results.get("n_anomalies_upward", 0))
    n_down = int(results.get("n_anomalies_downward", 0))
    most_extreme_date = results.get("most_extreme_date")
    most_extreme_z = results.get("most_extreme_z_score")
    if n_obs == 0:
        rate = 0.0
    else:
        rate = 100.0 * n_anom / n_obs
    if n_anom == 0:
        return (
            f"Seasonal-ESD detected no anomalies in "
            f"{format_series_reference(name)} ({n_obs} observations) "
            f"at alpha={FMT_P_VALUE.format(alpha)}. STL-adjusted "
            f"remainders are consistent with the null of no outliers "
            f"under the current threshold."
        )
    extreme_clause = ""
    if most_extreme_date and most_extreme_z is not None:
        extreme_clause = (
            f" Most extreme is the {most_extreme_date} event with "
            f"z-score {float(most_extreme_z):.1f} on STL-adjusted "
            f"remainders."
        )
    return (
        f"Seasonal-ESD detected {n_anom} anomal{'ies' if n_anom != 1 else 'y'} "
        f"({rate:.1f}% of {n_obs} observations) in "
        f"{format_series_reference(name)} at "
        f"alpha={FMT_P_VALUE.format(alpha)}. {n_up} upward and "
        f"{n_down} downward.{extreme_clause} Anomalies enumerated "
        f"with direction and severity in the data tables."
    )


def _tier2(results: dict) -> str:
    max_anomalies = results.get("max_anomalies")
    max_clause = (
        f"ESD iterates up to max_anomalies={int(max_anomalies)}"
        if max_anomalies is not None else "ESD iterates up to the configured maximum"
    )
    return (
        f"STL-decomposed series with generalized-ESD test on the "
        f"remainder component. Seasonal + trend removed before "
        f"anomaly scoring to avoid flagging routine-seasonal peaks as "
        f"anomalous. {max_clause}; each iteration's test statistic vs "
        f"critical value in the data tables. Alpha gives per-anomaly "
        f"false-positive protection; stricter thresholds (0.01) "
        f"reduce false positives at the cost of missing subtler "
        f"outliers."
    )


def _trigger_high_anomaly_rate(results: dict) -> Optional[str]:
    n_obs = int(results.get("n_obs", 0))
    n_anom = int(results.get("n_anomalies", 0))
    if n_obs == 0 or n_anom / n_obs <= 0.15:
        return None
    rate = 100.0 * n_anom / n_obs
    return (
        f"Anomaly rate {rate:.1f}% exceeds 15% — the threshold may be "
        f"too loose, OR the series contains a regime shift that the "
        f"ESD test is mistaking for outliers. Raise alpha or inspect "
        f"for a structural break."
    )


def _trigger_one_direction_only(results: dict) -> Optional[str]:
    n_up = int(results.get("n_anomalies_upward", 0))
    n_down = int(results.get("n_anomalies_downward", 0))
    if n_up + n_down < 5:
        return None
    if n_up > 0 and n_down > 0:
        return None
    direction = "upward" if n_up > 0 else "downward"
    return (
        f"All {n_up + n_down} detected anomalies are in the same "
        f"direction ({direction}). The series may have "
        f"heteroscedasticity rather than discrete outliers — large "
        f"deviations in one direction only suggest a variance shift "
        f"or asymmetric distribution, not outlier contamination."
    )


SPEC = InterpretationSpec(
    technique_id="stl_esd_anomaly",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_high_anomaly_rate, _trigger_one_direction_only),
    mode_aware=False,
)

register(SPEC)
