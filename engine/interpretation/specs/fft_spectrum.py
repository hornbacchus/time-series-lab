"""
InterpretationSpec for fft_spectrum (discrete Fourier transform).

Class 1 output (power-vs-frequency distribution). Shares the base
Tier 1 template with periodogram_spectral_density; Tier 2 augments
with FFT-specific disclosure (no tapering window, spectral leakage
considerations).
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


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    dom_period = results.get("dominant_period")
    dom_freq = results.get("dominant_frequency")
    top1_pct = results.get("top_peak_power_pct")
    top10_pct = results.get("top_peaks_power_pct")
    nyquist = results.get("nyquist_frequency", 0.5)
    window = str(results.get("window", "none")).lower()
    detrend = str(results.get("detrend", "none")).lower()
    if dom_period is None or dom_freq is None:
        return (
            f"FFT spectral analysis of {format_series_reference(name)} "
            f"({n} observations). No clearly-dominant peak identified; "
            f"the power distribution is broadband or very noisy."
        )
    band = power_concentration_band(top1_pct)
    top1_str = f"{float(top1_pct):.1f}" if top1_pct is not None else "(not reported)"
    top10_clause = (
        f"; top 10 peaks together account for {float(top10_pct):.1f}%"
        if top10_pct is not None else ""
    )
    nyquist_period = (1.0 / float(nyquist)) if nyquist and float(nyquist) > 0 else 0.0
    closer_parts = []
    if detrend not in ("none", "false"):
        closer_parts.append(f"Detrending applied ({detrend})")
    else:
        closer_parts.append("No detrending")
    if window in ("none", "false", ""):
        closer_parts.append(
            "no windowing — expect spectral leakage at sub-bin frequencies"
        )
    else:
        closer_parts.append(f"{window} windowing applied")
    closer = "; ".join(closer_parts) + "."
    return (
        f"FFT spectral analysis of {format_series_reference(name)} "
        f"({n} observations). Dominant period "
        f"{format_scale_aware(float(dom_period))} observations at "
        f"frequency {format_scale_aware(float(dom_freq))} cycles/obs "
        f"({band} concentration, {top1_str}% of total spectral power)"
        f"{top10_clause}. Nyquist limit "
        f"{format_scale_aware(float(nyquist))} cycles/obs (period of "
        f"{format_scale_aware(float(nyquist_period))} observations). "
        f"{closer}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    window = str(results.get("window", "none")).lower()
    detrend = str(results.get("detrend", "none")).lower()
    freq_res = results.get("frequency_resolution")
    freq_res_str = (
        format_scale_aware(float(freq_res)) if freq_res is not None
        else "1/n"
    )
    leakage_clause = (
        "The rectangular effective window introduces side-lobe "
        "leakage, which can smear isolated peaks by one to two "
        "frequency bins."
        if window in ("none", "false", "")
        else f"The {window} taper reduces side-lobe leakage at the cost "
        f"of slight main-lobe broadening."
    )
    return (
        f"Discrete Fourier Transform of the {detrend}-detrended series "
        f"(n={n}); spectral power computed as |FFT|² normalized by "
        f"sample length. {leakage_clause} Frequency resolution is "
        f"{freq_res_str} cycles/obs (1/n). Frequencies above Nyquist "
        f"alias into the observable band; no anti-aliasing filter was "
        f"applied by the wrapper, so any sub-sampling-period structure "
        f"in the raw series may contaminate the reported spectrum. FFT "
        f"assumes stationarity — a single spectrum summarizes time-"
        f"averaged spectral content and does not reveal regime changes "
        f"or time-varying cyclicality; for time-localized analysis, "
        f"use wavelet_transform."
    )


def _trigger_weak_concentration(results: dict) -> Optional[str]:
    top1 = results.get("top_peak_power_pct")
    if top1 is None or float(top1) >= 10.0:
        return None
    return (
        f"Dominant peak carries only {float(top1):.1f}% of total power "
        f"(weak concentration); the spectrum is broadband rather than "
        f"cyclic. A single-period summary may misrepresent the series' "
        f"structure — consider wavelet decomposition or structural "
        f"time-series modeling."
    )


def _trigger_no_windowing_on_long_series(results: dict) -> Optional[str]:
    window = str(results.get("window", "none")).lower()
    n = int(results.get("n_obs", 0))
    top1 = results.get("top_peak_power_pct")
    if window not in ("none", "false", ""):
        return None
    if n < 1000:
        return None
    if top1 is None or float(top1) < 10.0:
        return None
    return (
        f"No windowing applied on a long series; spectral leakage from "
        f"non-bin-aligned frequencies can inflate peak power by 5-15%. "
        f"Consider re-running with ``window='hann'`` for a cleaner peak "
        f"identification."
    )


SPEC = InterpretationSpec(
    technique_id="fft_spectrum",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_weak_concentration,
        _trigger_no_windowing_on_long_series,
    ),
    mode_aware=False,
)

register(SPEC)
