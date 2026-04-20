"""
InterpretationSpec for robust_estimators.

Per Decision 5: accepts audit-revealed univariate location/scale shape
(not regression). Tier 1 focuses on classical-vs-robust comparison.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_SIGNED,
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


# In-spec Std/MAD ratio bands. TODO: promote to C.8 primitive if a
# second spec in C2-C7 needs scale-ratio banding.
def _std_mad_ratio_band(ratio: float) -> str:
    r = float(ratio)
    if r < 1.3:
        return "well-behaved"
    if r < 1.8:
        return "mildly heavy-tailed"
    if r < 3.0:
        return "heavy-tailed"
    return "very heavy-tailed"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    mean_val = float(results.get("mean", 0.0))
    median_val = float(results.get("median", 0.0))
    std_val = float(results.get("std", 0.0))
    mad_scale = float(results.get("mad_scale", 0.0))
    gap = abs(mean_val - median_val)
    ratio = (std_val / mad_scale) if mad_scale > 0 else 0.0
    band = _std_mad_ratio_band(ratio)
    skew_direction = "right-skew or upper outliers" if mean_val > median_val else "left-skew or lower outliers" if mean_val < median_val else "symmetric"
    return (
        f"Robust location/scale summary of "
        f"{format_series_reference(name)} ({n} observations). Median "
        f"{FMT_COEF_SIGNED.format(median_val)} vs mean "
        f"{FMT_COEF_SIGNED.format(mean_val)}; gap of "
        f"{FMT_COEF_UNSIGNED.format(gap)} indicates "
        f"{skew_direction}. Std {FMT_COEF_UNSIGNED.format(std_val)} "
        f"vs MAD-based scale {FMT_COEF_UNSIGNED.format(mad_scale)}, "
        f"ratio {FMT_COEF_UNSIGNED.format(ratio)} — {band}; classical "
        f"summaries overstate typical dispersion."
    )


def _tier2(results: dict) -> str:
    mean_val = float(results.get("mean", 0.0))
    median_val = float(results.get("median", 0.0))
    trimmed_mean = results.get("trimmed_mean")
    huber_m = results.get("huber_m_estimate")
    std_val = float(results.get("std", 0.0))
    mad_scale = float(results.get("mad_scale", 0.0))
    iqr_scale = results.get("iqr_scale")
    qn_scale = results.get("qn_scale")
    location_sentence = (
        f"Four location estimators: mean "
        f"{FMT_COEF_SIGNED.format(mean_val)}, median "
        f"{FMT_COEF_SIGNED.format(median_val)}"
    )
    if trimmed_mean is not None:
        location_sentence += (
            f", 10%-trimmed mean {FMT_COEF_SIGNED.format(float(trimmed_mean))}"
        )
    if huber_m is not None:
        location_sentence += (
            f", Huber (c=1.345) M-estimate {FMT_COEF_SIGNED.format(float(huber_m))}"
        )
    location_sentence += "."
    scale_sentence = (
        f"Four scale estimators: std "
        f"{FMT_COEF_UNSIGNED.format(std_val)}, MAD (×1.4826) "
        f"{FMT_COEF_UNSIGNED.format(mad_scale)}"
    )
    if iqr_scale is not None:
        scale_sentence += f", IQR/1.349 {FMT_COEF_UNSIGNED.format(float(iqr_scale))}"
    if qn_scale is not None:
        scale_sentence += f", Q_n {FMT_COEF_UNSIGNED.format(float(qn_scale))}"
    scale_sentence += "."
    ratio = (std_val / mad_scale) if mad_scale > 0 else 0.0
    gap = abs(mean_val - median_val)
    interpretation = (
        f"Std/MAD ratio {FMT_COEF_UNSIGNED.format(ratio)} "
        f"{'exceeds 1.5×' if ratio > 1.5 else 'is near 1.0'} — "
        f"classical scale "
        f"{'inflated by outliers' if ratio > 1.5 else 'agrees with the robust estimate'}. "
        f"Mean-median gap {FMT_COEF_UNSIGNED.format(gap)} "
        f"{'exceeds 0.1×std — asymmetric distribution or tail contamination' if gap > 0.1 * std_val else 'is small relative to std — symmetry is plausible'}."
    )
    return f"{location_sentence} {scale_sentence} {interpretation}"


def _trigger_very_heavy_tails(results: dict) -> Optional[str]:
    std_val = results.get("std")
    mad_scale = results.get("mad_scale")
    if std_val is None or mad_scale is None or float(mad_scale) <= 0:
        return None
    ratio = float(std_val) / float(mad_scale)
    if ratio <= 3:
        return None
    return (
        f"Std/MAD ratio {FMT_COEF_UNSIGNED.format(ratio)} exceeds 3.0 "
        f"— very heavy tails. Classical methods (mean, std, normality-"
        f"assuming inference) are unreliable on this series; prefer "
        f"the robust summaries and consider heavy-tailed distributional "
        f"models downstream."
    )


def _trigger_well_behaved(results: dict) -> Optional[str]:
    std_val = results.get("std")
    mad_scale = results.get("mad_scale")
    mean_val = results.get("mean")
    median_val = results.get("median")
    if None in (std_val, mad_scale, mean_val, median_val):
        return None
    if float(mad_scale) <= 0:
        return None
    ratio = float(std_val) / float(mad_scale)
    gap = abs(float(mean_val) - float(median_val))
    if ratio >= 1.3 or gap >= 0.05 * float(std_val):
        return None
    return (
        "Both Std/MAD ratio < 1.3 and mean-median gap < 0.05×std — "
        "the series is well-behaved. Robust and classical estimates "
        "agree; either can be used interchangeably for downstream "
        "analysis."
    )


SPEC = InterpretationSpec(
    technique_id="robust_estimators",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_very_heavy_tails, _trigger_well_behaved),
    mode_aware=False,
)

register(SPEC)
