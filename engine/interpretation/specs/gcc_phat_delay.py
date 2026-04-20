"""
InterpretationSpec for gcc_phat_delay.

Signal-processing-style delay estimator. SNR + bootstrap CI replace
correlation + significance band.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _snr_word(snr: float) -> str:
    s = float(snr)
    if s < 3:
        return "low"
    if s < 5:
        return "moderate"
    return "high"


def _tier1(results: dict) -> str:
    x = str(results.get("series_name_x", "A"))
    y = str(results.get("series_name_y", "B"))
    delay_time = float(results.get("delay_time", 0.0))
    delay_units = str(results.get("delay_time_units", "seconds"))
    snr = float(results.get("snr", 0.0))
    ci_lo = results.get("ci_lower")
    ci_hi = results.get("ci_upper")
    lead_x = delay_time > 0
    lead_y = delay_time < 0
    if lead_x:
        direction = f"{format_series_reference(x)} leads {format_series_reference(y)}"
    elif lead_y:
        direction = f"{format_series_reference(y)} leads {format_series_reference(x)}"
    else:
        direction = f"{format_series_reference(x)} and {format_series_reference(y)} are synchronized"
    ci_clause = ""
    if ci_lo is not None and ci_hi is not None:
        ci_clause = (
            f" 95% bootstrap CI: [{FMT_COEF_UNSIGNED.format(float(ci_lo))}, "
            f"{FMT_COEF_UNSIGNED.format(float(ci_hi))}] {delay_units}."
        )
    return (
        f"{direction} by {FMT_COEF_UNSIGNED.format(abs(delay_time))} "
        f"{delay_units} (estimated delay via GCC-PHAT, SNR={snr:.1f} "
        f"indicating {_snr_word(snr)} confidence).{ci_clause} The "
        f"phase-transform weighting rejects in-band noise."
    )


def _tier2(results: dict) -> str:
    delay_samples = results.get("delay_samples")
    sample_rate = results.get("sample_rate_hz")
    weighting = str(results.get("weighting", "phat"))
    n_bootstrap = results.get("n_bootstrap")
    rate_clause = ""
    if sample_rate is not None:
        rate_clause = f" at {int(sample_rate)} Hz"
    bootstrap_clause = ""
    if n_bootstrap is not None:
        bootstrap_clause = (
            f" Bootstrap over {int(n_bootstrap)} resamples produces the 95% CI."
        )
    samples_clause = (
        f"Peak of the GCC function at lag {int(delay_samples)} samples{rate_clause}."
        if delay_samples is not None else ""
    )
    return (
        f"Generalized cross-correlation with {weighting.upper()} "
        f"weighting: each frequency bin normalized by its magnitude, "
        f"yielding a delay-robust estimator. {samples_clause} SNR "
        f"computed from peak height vs median-around-peak."
        f"{bootstrap_clause} Unlike CCF, GCC-PHAT is preferred for "
        f"signals dominated by a single delay plus noise; less "
        f"appropriate for weakly correlated or multi-path signals."
    )


def _trigger_low_snr(results: dict) -> Optional[str]:
    snr = results.get("snr")
    if snr is None or float(snr) >= 3:
        return None
    return (
        f"SNR={float(snr):.1f} is below 3; delay-estimate confidence "
        f"is low. Consider widening the bootstrap resample count, "
        f"inspecting the GCC function for multiple peaks, or "
        f"verifying that the pair is genuinely delay-related rather "
        f"than correlated for other reasons."
    )


def _trigger_wide_ci(results: dict) -> Optional[str]:
    ci_lo = results.get("ci_lower")
    ci_hi = results.get("ci_upper")
    delay = results.get("delay_time")
    if ci_lo is None or ci_hi is None or delay is None:
        return None
    width = abs(float(ci_hi) - float(ci_lo))
    if abs(float(delay)) <= 0:
        return None
    if width <= 0.2 * abs(float(delay)):
        return None
    return (
        f"CI width {width:.3f} exceeds 20% of the point estimate "
        f"{abs(float(delay)):.3f}. Delay uncertainty is large "
        f"relative to the magnitude; treat the estimate as a rough "
        f"guide rather than a precise value."
    )


SPEC = InterpretationSpec(
    technique_id="gcc_phat_delay",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_low_snr, _trigger_wide_ci),
    mode_aware=False,
)

register(SPEC)
