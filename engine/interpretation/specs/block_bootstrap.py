"""
InterpretationSpec for block_bootstrap.

Per V2 rewrite: Tier 2 restructures "(point X, bias Y, SE Z)" shape
into grammatical prose to pass T9 dangling-stat check.
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


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    block_length = int(results.get("block_length", 0))
    n_resamples = int(results.get("n_resamples", 0))
    mean_ci_lo = results.get("mean_ci_lower")
    mean_ci_hi = results.get("mean_ci_upper")
    var_ci_lo = results.get("variance_ci_lower")
    var_ci_hi = results.get("variance_ci_upper")
    acf1_ci_lo = results.get("acf1_ci_lower")
    acf1_ci_hi = results.get("acf1_ci_upper")
    mean_excludes_zero = (
        mean_ci_lo is not None and mean_ci_hi is not None and
        (float(mean_ci_lo) > 0 or float(mean_ci_hi) < 0)
    )
    mean_clause = ""
    if mean_ci_lo is not None and mean_ci_hi is not None:
        mean_clause = (
            f" Mean CI [{FMT_COEF_SIGNED.format(float(mean_ci_lo))}, "
            f"{FMT_COEF_SIGNED.format(float(mean_ci_hi))}] "
            f"{'excludes zero' if mean_excludes_zero else 'covers zero'} "
            f"at the 5% level — sample mean is "
            f"{'statistically non-zero' if mean_excludes_zero else 'not statistically distinguishable from zero'}."
        )
    var_clause = ""
    if var_ci_lo is not None and var_ci_hi is not None:
        var_clause = (
            f" Variance CI [{FMT_COEF_UNSIGNED.format(float(var_ci_lo))}, "
            f"{FMT_COEF_UNSIGNED.format(float(var_ci_hi))}]"
        )
    acf_clause = ""
    if acf1_ci_lo is not None and acf1_ci_hi is not None:
        acf_clause = (
            f" and ACF(1) CI [{FMT_COEF_SIGNED.format(float(acf1_ci_lo))}, "
            f"{FMT_COEF_SIGNED.format(float(acf1_ci_hi))}] included for reference."
        )
    return (
        f"Block bootstrap 95% CIs for {format_series_reference(name)} "
        f"({n} observations, block length {block_length}, "
        f"{n_resamples} resamples).{mean_clause}{var_clause}{acf_clause}"
    )


def _tier2(results: dict) -> str:
    block_length = int(results.get("block_length", 0))
    mean_point = results.get("mean_point")
    mean_bias = results.get("mean_bias")
    mean_se = results.get("mean_se")
    var_point = results.get("variance_point")
    var_se = results.get("variance_se")
    acf1_point = results.get("acf1_point")
    acf1_se = results.get("acf1_se")
    mean_sentence = (
        f"The mean estimate was "
        f"{FMT_COEF_SIGNED.format(float(mean_point))} with bias "
        f"{FMT_COEF_SIGNED.format(float(mean_bias))} and SE "
        f"{FMT_COEF_UNSIGNED.format(float(mean_se))}."
        if (mean_point is not None and mean_bias is not None and mean_se is not None)
        else "Mean estimate and bootstrap moments in the data tables."
    )
    var_sentence = (
        f"The variance estimate was "
        f"{FMT_COEF_UNSIGNED.format(float(var_point))} with SE "
        f"{FMT_COEF_UNSIGNED.format(float(var_se))}."
        if (var_point is not None and var_se is not None)
        else ""
    )
    acf_sentence = (
        f"The ACF(1) estimate was "
        f"{FMT_COEF_SIGNED.format(float(acf1_point))} with SE "
        f"{FMT_COEF_UNSIGNED.format(float(acf1_se))}."
        if (acf1_point is not None and acf1_se is not None)
        else ""
    )
    sentences = [
        f"Non-overlapping block bootstrap with block length {block_length} calibrated to the series autocorrelation scale.",
        mean_sentence, var_sentence, acf_sentence,
        "Reference comparisons: mean CI vs zero is the primary actionable fact; variance and ACF(1) CIs provide context for distributional assumptions downstream consumers may make.",
    ]
    return " ".join(s for s in sentences if s)


def _trigger_wide_ci(results: dict) -> Optional[str]:
    mean_point = results.get("mean_point")
    mean_ci_lo = results.get("mean_ci_lower")
    mean_ci_hi = results.get("mean_ci_upper")
    if mean_point is None or mean_ci_lo is None or mean_ci_hi is None:
        return None
    width = abs(float(mean_ci_hi) - float(mean_ci_lo))
    if abs(float(mean_point)) <= 0:
        return None
    if width <= abs(float(mean_point)):
        return None
    return (
        f"Mean CI width {FMT_COEF_UNSIGNED.format(width)} exceeds the "
        f"point estimate magnitude. Evidence about the mean's sign "
        f"and size is weak; consider a longer sample or a different "
        f"bootstrap block length."
    )


def _trigger_high_bias(results: dict) -> Optional[str]:
    mean_point = results.get("mean_point")
    mean_bias = results.get("mean_bias")
    if mean_point is None or mean_bias is None:
        return None
    if abs(float(mean_point)) <= 0:
        return None
    if abs(float(mean_bias)) <= 0.1 * abs(float(mean_point)):
        return None
    return (
        f"Bootstrap bias {FMT_COEF_SIGNED.format(float(mean_bias))} "
        f"exceeds 10% of the point estimate — substantial bias. The "
        f"block length may be too short for the series' "
        f"autocorrelation scale; try a longer block."
    )


SPEC = InterpretationSpec(
    technique_id="block_bootstrap",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_wide_ci, _trigger_high_bias),
    mode_aware=False,
)

register(SPEC)
