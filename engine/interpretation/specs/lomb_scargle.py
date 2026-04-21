"""
InterpretationSpec for lomb_scargle (Lomb-Scargle periodogram).

Class 1 shape (shared with fft_spectrum and periodogram_spectral_density
in Tier 1), but Tier 2 augments with FAP significance machinery and
the D2 regular-sampling disclosure. Per Decision 11, the spec converts
the wrapper's seconds-scale period (when ctx.time contained date
strings) to ctx.frequency natural units at render time.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._frequency_common import (
    power_concentration_band,
    convert_period_to_native,
)

PRESET_GATED_KEYS = ()


# FAP significance bands (Decision 10, astronomical convention).
def _fap_band(fap):
    """Map a false-alarm probability to a significance adjective."""
    if fap is None:
        return None
    try:
        f = float(fap)
    except Exception:
        return None
    if f < 0.001:
        return "highly significant"
    if f < 0.01:
        return "significant"
    if f < 0.05:
        return "marginal"
    return "not significant"


def _format_fap(fap):
    """Render a FAP value including the '> 10%' sentinel emitted by
    the wrapper when the exact FAP exceeds the tabulation threshold."""
    if fap is None:
        return "(not reported)"
    if isinstance(fap, str):
        return fap  # e.g. "> 10%"
    try:
        f = float(fap)
    except Exception:
        return str(fap)
    if f < 1e-4:
        return "< 0.0001"
    return FMT_P_VALUE.format(f)


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    dom_period_raw = results.get("dominant_period")
    dom_freq = results.get("dominant_frequency")
    max_power = results.get("max_power")
    fap = results.get("fap_at_dominant_peak")
    freq_code = results.get("frequency", "")
    time_span = results.get("time_span")
    sampling_cv = results.get("sampling_irregularity_cv")

    if dom_period_raw is None or dom_freq is None:
        return (
            f"Lomb-Scargle periodogram of {format_series_reference(name)} "
            f"({n} observations). No clearly-dominant peak identified."
        )

    # D11: convert period to natural units when the wrapper's time
    # axis was seconds-scale.
    period_native, units_label = convert_period_to_native(
        float(dom_period_raw), freq_code, n_obs=n, time_span=time_span,
    )
    # Power share: LS normalized power is bounded [0, 1], so we treat
    # max_power as the peak's share of total normalized power (×100).
    share_pct = float(max_power) * 100.0 if max_power is not None else None
    band = power_concentration_band(share_pct)
    share_str = f"{share_pct:.1f}%" if share_pct is not None else "(share not reported)"

    fap_str = _format_fap(fap)
    fap_band = _fap_band(fap) if not isinstance(fap, str) else None
    if isinstance(fap, str):
        # Wrapper returned a sentinel like "> 10%" — map to not-significant
        fap_band = "not significant"
    fap_clause = (
        f"false-alarm probability {fap_str} ({fap_band}) under the "
        f"Baluev analytic null"
        if fap_band else
        f"false-alarm probability {fap_str}"
    )

    # Regular-vs-irregular sampling disclosure
    regular_clause = ""
    if sampling_cv is not None and float(sampling_cv) < 0.01:
        regular_clause = (
            " The series is regularly sampled; Lomb-Scargle degenerates "
            "toward the ordinary periodogram."
        )

    period_str = format_scale_aware(float(period_native))
    freq_str = format_scale_aware(float(dom_freq))
    return (
        f"Lomb-Scargle periodogram of {format_series_reference(name)} "
        f"({n} observations). Dominant period {period_str} {units_label} "
        f"at frequency {freq_str} cycles/obs ({share_str} of total "
        f"normalized power, {band} concentration); {fap_clause}."
        f"{regular_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    fap_method = str(results.get("fap_method", "baluev")).lower()
    oversampling = results.get("oversampling")
    n_freqs = results.get("n_freqs")
    fap = results.get("fap_at_dominant_peak")
    sampling_cv = results.get("sampling_irregularity_cv")

    oversample_str = (
        f"oversampling factor {int(oversampling)}" if oversampling else
        "default oversampling"
    )
    bins_str = (
        f"{int(n_freqs)} frequency bins scanned" if n_freqs else
        "frequency bins scanned"
    )
    # FAP method description
    if fap_method == "baluev":
        fap_desc = (
            "False-alarm probability computed analytically (Baluev 2008) — "
            "appropriate for unevenly-sampled data; bootstrap permutation "
            "is available under the Thorough preset for robust FAP "
            "estimates at the cost of ~100× compute."
        )
    elif fap_method == "bootstrap":
        fap_desc = (
            "False-alarm probability computed via bootstrap permutation "
            "(Thorough preset); Baluev analytic approximation is the "
            "default for Fast and Balanced presets."
        )
    else:
        fap_desc = f"False-alarm probability computed via {fap_method}."

    # Per-peak FAP caveat
    fap_caveat = ""
    if isinstance(fap, (float, int)) and fap is not None:
        fap_caveat = (
            f" The peak FAP of {_format_fap(fap)} corresponds to the "
            f"probability that the peak arises under a random white-noise "
            f"null given the search bandwidth; this is a per-peak (not "
            f"per-spectrum) significance level and does not apply a "
            f"multi-testing correction across the {bins_str.split()[0] if n_freqs else 'searched'} "
            f"frequencies."
        )

    # D2 addition: regular-sampling degeneracy disclosure
    regular_disclosure = ""
    if sampling_cv is not None and float(sampling_cv) < 0.01:
        regular_disclosure = (
            f" This series is regularly sampled (sampling_irregularity_cv "
            f"= {format_scale_aware(float(sampling_cv))}, near zero); "
            f"Lomb-Scargle degenerates toward the ordinary periodogram on "
            f"regularly sampled data. Consider periodogram_spectral_density "
            f"for a more direct estimation; the dominant period should "
            f"match the ordinary periodogram's report within ~1 frequency "
            f"bin."
        )

    return (
        f"Lomb-Scargle periodogram via scipy.signal.lombscargle (normalized) "
        f"on {n} observations, {oversample_str}, {bins_str}. {fap_desc}"
        f"{fap_caveat}{regular_disclosure}"
    )


def _trigger_peak_not_significant(results: dict) -> Optional[str]:
    fap = results.get("fap_at_dominant_peak")
    if fap is None:
        return None
    # Handle the wrapper's string sentinel "> 10%"
    if isinstance(fap, str):
        if "> 10" in fap:
            return (
                f"Dominant peak has false-alarm probability {fap}, which "
                f"exceeds the 5% threshold; the peak is not statistically "
                f"distinguishable from red-noise at standard significance "
                f"levels. Either the cycle is genuinely weak in this data "
                f"window, or a longer sample is needed to resolve it above "
                f"the noise floor."
            )
        return None
    try:
        f = float(fap)
    except Exception:
        return None
    if f < 0.05:
        return None
    return (
        f"Dominant peak has false-alarm probability {_format_fap(f)} under "
        f"the Baluev null, exceeding the 5% threshold; the peak is not "
        f"statistically distinguishable from red-noise at standard "
        f"significance levels. Either the cycle is genuinely weak in this "
        f"data window, or a longer sample is needed to resolve it above "
        f"the noise floor."
    )


def _trigger_on_regular_data(results: dict) -> Optional[str]:
    sampling_cv = results.get("sampling_irregularity_cv")
    if sampling_cv is None or float(sampling_cv) >= 0.01:
        return None
    return (
        f"Input data is effectively regularly sampled "
        f"(CV = {format_scale_aware(float(sampling_cv))} < 0.01); Lomb-"
        f"Scargle's primary advantage over FFT/periodogram is irregular-"
        f"sampling robustness, which is not exercised here. Results should "
        f"closely match periodogram_spectral_density; if they diverge "
        f"materially, this indicates a wrapper or unit-conversion "
        f"inconsistency."
    )


SPEC = InterpretationSpec(
    technique_id="lomb_scargle",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_peak_not_significant,
        _trigger_on_regular_data,
    ),
    mode_aware=False,
)

register(SPEC)
