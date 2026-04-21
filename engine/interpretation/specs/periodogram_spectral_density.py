"""
InterpretationSpec for periodogram_spectral_density (raw periodogram).

Class 1 output. Shares the Tier 1 base template with fft_spectrum
but Tier 2 frames the estimator as "raw periodogram via scipy.signal"
with the variance-vs-bias trade-off honest-disclosure and a pointer
to Welch / multitaper alternatives for long series.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._frequency_common import power_concentration_band

PRESET_GATED_KEYS = ()


def _entropy_descriptor(entropy):
    """Normalized spectral entropy (0-1): 0 = concentrated, 1 = broadband."""
    if entropy is None:
        return None
    e = float(entropy)
    if e < 0.3: return "highly concentrated"
    if e < 0.6: return "moderate"
    if e < 0.85: return "broadband"
    return "nearly flat (white-noise-like)"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    dom_period = results.get("dominant_period")
    dom_freq = results.get("dominant_frequency")
    top1_pct = results.get("top_peak_power_pct")
    entropy = results.get("spectral_entropy")
    freq_res = results.get("frequency_resolution")
    nyquist = results.get("nyquist_frequency", 0.5)
    estimator = str(results.get("estimator_variant", "raw")).lower()
    entropy_desc = _entropy_descriptor(entropy)
    if dom_period is None or dom_freq is None:
        return (
            f"Periodogram spectral density of {format_series_reference(name)} "
            f"({n} observations). No clearly-dominant peak identified; "
            f"power distribution is broadband."
        )
    band = power_concentration_band(top1_pct)
    top1_str = f"{float(top1_pct):.1f}" if top1_pct is not None else "(not reported)"
    entropy_clause = (
        f" Spectral entropy {float(entropy):.2f} ({entropy_desc} distribution — "
        f"power spreads across multiple frequencies rather than concentrating "
        f"on a single tone)."
        if entropy is not None else ""
    )
    estimator_closer = (
        "Estimator is raw periodogram (unbiased but inconsistent); for "
        "variance reduction on long series consider Welch's method."
        if estimator == "raw" else
        f"Estimator: {estimator}."
    )
    return (
        f"Periodogram spectral density of {format_series_reference(name)} "
        f"({n} observations). Dominant period "
        f"{format_scale_aware(float(dom_period))} observations at "
        f"frequency {format_scale_aware(float(dom_freq))} cycles/obs "
        f"({band} concentration, {top1_str}% of total spectral power)."
        f"{entropy_clause} Nyquist limit "
        f"{format_scale_aware(float(nyquist))} cycles/obs"
        + (f"; frequency resolution {format_scale_aware(float(freq_res))}."
           if freq_res is not None else ".")
        + f" {estimator_closer}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    window = str(results.get("window", "none"))
    detrend = str(results.get("detrend", "false"))
    n_bins = results.get("n_freq_bins")
    freq_res = results.get("frequency_resolution")
    total_power = results.get("total_power")
    entropy = results.get("spectral_entropy")
    centroid = results.get("spectral_centroid")
    bandwidth = results.get("spectral_bandwidth")
    edge95 = results.get("spectral_edge_95")
    bins_str = f"{int(n_bins)} frequency bins" if n_bins else "frequency bins"
    res_str = format_scale_aware(float(freq_res)) if freq_res is not None else "(not reported)"
    total_str = format_scale_aware(float(total_power)) if total_power is not None else "(not reported)"
    entropy_str = format_scale_aware(float(entropy)) if entropy is not None else "(not reported)"
    centroid_str = format_scale_aware(float(centroid)) if centroid is not None else "(not reported)"
    bandwidth_str = format_scale_aware(float(bandwidth)) if bandwidth is not None else "(not reported)"
    edge95_str = format_scale_aware(float(edge95)) if edge95 is not None else "(not reported)"
    return (
        f"Raw periodogram via scipy.signal.periodogram, no segment "
        f"averaging (not Welch), no multitaper. {window.capitalize()}-window "
        f"tapered, {detrend}-detrended series (n={n}) produces {bins_str} "
        f"at resolution {res_str} cycles/obs. Total power {total_str} "
        f"(units: squared-series-units per frequency bin). Spectral "
        f"entropy {entropy_str}; spectral centroid {centroid_str} "
        f"cycles/obs; spectral bandwidth {bandwidth_str} cycles/obs; "
        f"95% of total power lies below {edge95_str} cycles/obs. Raw "
        f"periodogram is a consistent-bias but high-variance estimator — "
        f"adjacent frequency bins are uncorrelated yet each bin's sampling "
        f"variance is ~σ² itself, not reduced by averaging. For series > "
        f"1000 observations, Welch's method with 50% segment overlap "
        f"reduces variance at the cost of frequency resolution; multitaper "
        f"(Thomson) is preferred for sharp-peak identification under "
        f"variance constraint."
    )


def _trigger_weak_concentration(results: dict) -> Optional[str]:
    top1 = results.get("top_peak_power_pct")
    if top1 is None or float(top1) >= 10.0:
        return None
    return (
        f"Dominant peak carries only {float(top1):.1f}% of total power "
        f"(weak concentration); the spectrum is broadband rather than "
        f"cyclic."
    )


def _trigger_raw_periodogram_long_series(results: dict) -> Optional[str]:
    estimator = str(results.get("estimator_variant", "raw")).lower()
    n = int(results.get("n_obs", 0))
    if estimator != "raw" or n < 1000:
        return None
    return (
        f"Raw periodogram on {n} observations; sampling variance per "
        f"frequency bin is not reduced by segment averaging. For "
        f"variance-tight applications, re-run via Welch's method or "
        f"multitaper."
    )


SPEC = InterpretationSpec(
    technique_id="periodogram_spectral_density",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_weak_concentration,
        _trigger_raw_periodogram_long_series,
    ),
    mode_aware=False,
)

register(SPEC)
