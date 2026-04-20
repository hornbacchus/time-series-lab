"""
InterpretationSpec for dtw_alignment_lag.

Per Decision C: no qualitative distance bands. Cite the normalized
DTW distance as a raw number with the "lower = more similar" framing.
Per V1: bare parenthetical "(std 4 days)" rewritten to citation form
"std of 4 days".
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
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    dist = float(results.get("dtw_normalized", 0.0))
    median_lag = results.get("median_lag")
    lag_std = results.get("lag_std")
    n_x = int(results.get("n_x", 0))
    n_y = int(results.get("n_y", 0))
    lag_clause = ""
    if median_lag is not None:
        lag_clause = f" Median warp lag {int(median_lag)} periods"
    std_clause = ""
    if lag_std is not None:
        std_clause = f" with lag std of {float(lag_std):.2f} periods, indicating time-varying lead-lag"
    return (
        f"DTW alignment distance "
        f"{FMT_COEF_UNSIGNED.format(dist)} (normalized by path length) "
        f"between {format_series_reference(x)} and "
        f"{format_series_reference(y)} ({n_x} and {n_y} observations)."
        f"{lag_clause}{std_clause}. Lower normalized distance "
        f"indicates closer alignment; interpret relative to the "
        f"chosen Sakoe-Chiba band and the series magnitudes."
    )


def _tier2(results: dict) -> str:
    band = results.get("sakoe_chiba_band")
    path_length = results.get("path_length")
    diag_length = results.get("diag_length")
    distortion = results.get("distortion_ratio")
    band_clause = (
        f"Sakoe-Chiba band of {int(band)} samples"
        if band is not None else "Sakoe-Chiba band specified by preset"
    )
    path_clause = ""
    if path_length is not None and diag_length is not None:
        path_clause = (
            f" Warp path length {int(path_length)} vs diagonal "
            f"{int(diag_length)}"
        )
    distortion_clause = ""
    if distortion is not None:
        distortion_clause = f"; distortion ratio {float(distortion):.2f}"
    return (
        f"Dynamic time warping with {band_clause}.{path_clause}"
        f"{distortion_clause}. Time-varying lag extracted from the "
        f"warp path gradient; segment-level lag summary in the data "
        f"tables. DTW is complementary to CCF: it handles non-linear "
        f"alignment that correlation misses, but does not provide a "
        f"significance band — distance interpretation is relative to "
        f"the series magnitudes and the chosen band constraint."
    )


def _trigger_severe_warping(results: dict) -> Optional[str]:
    distortion = results.get("distortion_ratio")
    if distortion is None or float(distortion) <= 2.0:
        return None
    return (
        f"Distortion ratio {float(distortion):.2f} exceeds 2.0; the "
        f"warp path deviates far from the diagonal. Alignment is "
        f"poor, and the DTW distance should not be interpreted as a "
        f"similarity score. CCF on this pair may also be unreliable."
    )


def _trigger_highly_variable_lag(results: dict) -> Optional[str]:
    lag_std = results.get("lag_std")
    max_lag = results.get("max_lag")
    if lag_std is None or max_lag is None or float(max_lag) <= 0:
        return None
    if float(lag_std) <= 0.5 * float(max_lag):
        return None
    return (
        f"Lag std {float(lag_std):.2f} exceeds 50% of the max lag "
        f"{int(max_lag)}. The lag is highly time-varying; a single-"
        f"number summary is misleading. Examine the segment-level "
        f"lag series to characterize the variation."
    )


SPEC = InterpretationSpec(
    technique_id="dtw_alignment_lag",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_severe_warping, _trigger_highly_variable_lag),
    mode_aware=False,
)

register(SPEC)
