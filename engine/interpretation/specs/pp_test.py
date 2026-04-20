"""
InterpretationSpec for pp_test standalone invocation.

Null = unit root (mirrors ADF). Delegates tier rendering to
`_stationarity_common.render_stationarity_tier` keyed on
null_direction='unit_root'.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_STAT_DEFAULT,
)
from interpretation.registry import register
from interpretation.specs._stationarity_common import render_stationarity_tier

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    return render_stationarity_tier(
        tier=1,
        test_name="PP",
        null_direction="unit_root",
        rejected=bool(results.get("rejected", False)),
        series_name=str(results.get("series_name", "the series")),
        stat_value=float(results.get("stat_value", 0.0)),
        p_value=results.get("p_value"),
        crit_value=float(results.get("crit_value", 0.0)),
        significance=float(results.get("significance", 0.05)),
        regression=str(results.get("regression", "c")),
        sample_size=int(results.get("n_obs", 0)),
        bandwidth=results.get("bandwidth"),
        trending=results.get("trending"),
        effective_sample_size=results.get("effective_sample_size"),
        pvalue_clipped=bool(results.get("pvalue_clipped", False)),
    )


def _tier2(results: dict) -> str:
    return render_stationarity_tier(
        tier=2,
        test_name="PP",
        null_direction="unit_root",
        rejected=bool(results.get("rejected", False)),
        series_name=str(results.get("series_name", "the series")),
        stat_value=float(results.get("stat_value", 0.0)),
        p_value=results.get("p_value"),
        crit_value=float(results.get("crit_value", 0.0)),
        significance=float(results.get("significance", 0.05)),
        regression=str(results.get("regression", "c")),
        sample_size=int(results.get("n_obs", 0)),
        bandwidth=results.get("bandwidth"),
        trending=results.get("trending"),
        effective_sample_size=results.get("effective_sample_size"),
        pvalue_clipped=bool(results.get("pvalue_clipped", False)),
    )


def _trigger_borderline(results: dict) -> Optional[str]:
    stat = results.get("stat_value")
    crit = results.get("crit_value")
    if stat is None or crit is None:
        return None
    diff = abs(float(stat) - float(crit))
    if diff > 0.10 * abs(float(crit)):
        return None
    return (
        f"Z(t)={FMT_STAT_DEFAULT.format(float(stat))} is within 10% of "
        f"the critical value {FMT_STAT_DEFAULT.format(float(crit))}. "
        f"Verdict is borderline; ADF + KPSS joint triage is advisable."
    )


def _trigger_trending_constant_regression(results: dict) -> Optional[str]:
    if not bool(results.get("trending", False)):
        return None
    if str(results.get("regression", "c")) != "c":
        return None
    return (
        "The series exhibits a linear trend but the test was run with "
        "regression='c' (constant-only). Re-run with regression='ct' "
        "for a trend-stationarity specification."
    )


SPEC = InterpretationSpec(
    technique_id="pp_test",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_borderline, _trigger_trending_constant_regression),
    mode_aware=False,
)

register(SPEC)
