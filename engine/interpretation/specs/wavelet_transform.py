"""
InterpretationSpec for wavelet_transform (discrete wavelet transform).

Class 4 (component decomposition) per Phase 2 refinement — DWT output
is a set of reconstructed time series per dyadic frequency band, not a
2D scalogram heatmap.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _energy_concentration_band(pct):
    """Reuse power-concentration band semantics for DWT energy shares."""
    if pct is None:
        return "unknown"
    s = float(pct)
    if s < 10.0:
        return "weak"
    if s < 30.0:
        return "moderate"
    if s < 60.0:
        return "strong"
    return "dominant"


def _second_highest_detail(results: dict):
    """Find the second-highest-energy detail band for Tier 1 context
    when the Approximation dominates totally."""
    energies = results.get("detail_band_energies_pct") or {}
    if not energies:
        return None, None, None
    # Sort by energy pct descending
    sorted_bands = sorted(energies.items(), key=lambda kv: -float(kv[1]))
    if not sorted_bands:
        return None, None, None
    name, pct = sorted_bands[0]
    period_range = (results.get("detail_band_periods") or {}).get(name)
    return name, float(pct), period_range


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    wavelet = str(results.get("wavelet", "db4"))
    level = int(results.get("level", 1))
    max_level = int(results.get("max_level", level))
    dom_comp = str(results.get("dominant_component", "Approximation (A)"))
    dom_pct = results.get("dominant_energy_pct")
    dom_period_range = results.get("dominant_band_period_range")

    band = _energy_concentration_band(dom_pct)
    pct_str = f"{float(dom_pct):.1f}" if dom_pct is not None else "(not reported)"
    max_level_note = (
        f"{level} decomposition levels (maximum possible for this series length)"
        if level == max_level else
        f"{level} decomposition levels (max possible {max_level})"
    )
    dom_clause = f"Dominant component: {dom_comp}"
    if dom_period_range:
        dom_clause += f" (period {dom_period_range})"
    dom_clause += f" at {pct_str}% of total energy ({band} concentration)."

    # Second-highest detail band for context
    d2_name, d2_pct, d2_period = _second_highest_detail(results)
    d2_clause = ""
    if d2_name and d2_pct is not None:
        d2_label = d2_name.replace("Detail ", "")
        period_note = f" (period {d2_period})" if d2_period else ""
        d2_clause = (
            f" {d2_name} {period_note} at {d2_pct:.2f}%"
            if d2_pct >= 0.5 else
            ""
        )

    return (
        f"Discrete Wavelet Transform of {format_series_reference(name)} "
        f"({n} observations) using {wavelet} wavelet at "
        f"{max_level_note}. {dom_clause}{d2_clause}"
    )


def _tier2(results: dict) -> str:
    wavelet = str(results.get("wavelet", "db4"))
    mode = str(results.get("mode", "symmetric"))
    level = int(results.get("level", 1))
    filter_length = results.get("filter_length")
    filter_clause = (
        f"Filter length is {int(filter_length)} samples; reconstructed "
        f"components within the first or last ~{int(filter_length)} "
        f"samples of the series carry boundary artifacts from the "
        f"{mode} extension and should be interpreted with caution near "
        f"the edges."
        if filter_length else
        f"Filter length not reported; typical boundary artifacts apply "
        f"within ~filter_length samples of each edge."
    )
    # Band definitions
    bands_lines = []
    for i in range(1, level + 1):
        bands_lines.append(f"D{i} (period {2**i}-{2**(i+1)} obs)")
    bands_str = ", ".join(bands_lines) if bands_lines else "detail bands"
    return (
        f"DWT decomposition via PyWavelets with '{wavelet}' wavelet and "
        f"{mode} boundary extension. Output is reconstructed time series "
        f"per dyadic frequency band (not a continuous time-frequency "
        f"scalogram). The {level} decomposition levels yield a trend "
        f"(Approximation, period > {2**(level+1)} obs) plus {level} "
        f"detail bands spanning dyadic octaves: {bands_str}. Frequency "
        f"translation uses the DWT dyadic octave convention — continuous-"
        f"scale interpretations (e.g., Morlet-CWT period ≈ 1.03·scale) "
        f"do not apply. {filter_clause} Energy per component is not "
        f"normalized for reconstruction dimensionality — longer-period "
        f"bands (lower-frequency) aggregate coefficients from fewer "
        f"downsampled indices, so raw energy shares favor coarse scales."
    )


def _trigger_approximation_dominates(results: dict) -> Optional[str]:
    dom_comp = str(results.get("dominant_component", ""))
    dom_pct = results.get("dominant_energy_pct")
    if dom_pct is None or float(dom_pct) < 95.0:
        return None
    if "Approximation" not in dom_comp:
        return None
    return (
        f"Approximation band carries {float(dom_pct):.1f}% of total "
        f"energy — the series is overwhelmingly trend-dominant in the "
        f"{results.get('wavelet', 'selected')} basis. Consider "
        f"differencing or detrending before DWT to expose oscillatory "
        f"structure in the detail bands; as fitted, the detail bands "
        f"are effectively numerical residuals."
    )


def _trigger_short_series_for_max_level(results: dict) -> Optional[str]:
    level = int(results.get("level", 0))
    max_level = int(results.get("max_level", 0))
    n = int(results.get("n_obs", 0))
    if level != max_level or level == 0:
        return None
    # Heuristic: trend-vs-noise separation is fragile when n / 2^level < 16
    threshold = 2 ** level
    if n >= 16 * threshold:
        return None
    coefs_at_coarsest = max(1, n // threshold)
    return (
        f"Decomposition at level {level} (max possible) on only {n} "
        f"observations — each detail band at level {level} is "
        f"reconstructed from fewer than {coefs_at_coarsest} coefficients. "
        f"Trend-vs-noise separation at the coarsest scale is numerically "
        f"fragile; consider reducing to level {level - 1} for cleaner "
        f"scale-localized estimates."
    )


SPEC = InterpretationSpec(
    technique_id="wavelet_transform",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_approximation_dominates,
        _trigger_short_series_for_max_level,
    ),
    mode_aware=False,
)

register(SPEC)
