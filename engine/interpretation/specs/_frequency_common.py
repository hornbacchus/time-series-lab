"""
Shared helpers for Prompt C4 Frequency Domain interpretation specs.

Leading-underscore filename marks this as spec-internal (not a
registered spec). Used by fft_spectrum, periodogram_spectral_density,
and lomb_scargle for the shared power-concentration adjective band.
Other C4 specs (wavelet_transform, wavelet_coherence, ssa_model,
emd_hht) have distinct Tier 1 shapes and do not route through this.
"""


# Power-concentration adjective bands (Prompt C4 Decision 6).
# Applied to the dominant peak's share of total spectral power.
# TODO: promote to a shared primitive on the second distinct use
# outside the spectral family (e.g., if a future wavelet or
# energy-decomposition spec needs the same "concentration" language).
def power_concentration_band(share_pct):
    """Map a power share percentage (0-100 scale) to an adjective band.

    - < 10%   → "weak"
    - 10-30%  → "moderate"
    - 30-60%  → "strong"
    - ≥ 60%   → "dominant"

    Used by the three spectral-density specs for Tier 1 rendering
    of dominant-peak concentration.
    """
    if share_pct is None:
        return "unknown"
    s = float(share_pct)
    if s < 10.0:
        return "weak"
    if s < 30.0:
        return "moderate"
    if s < 60.0:
        return "strong"
    return "dominant"


# Lomb-Scargle time-axis unit conversion (Prompt C4 Decision 11).
# The wrapper derives its time axis from ctx.time date strings,
# converting to seconds since epoch. That produces period values in
# seconds (e.g., 347M s ≈ 11 years on monthly sunspots), which is
# unreadable. This helper converts the raw wrapper-reported period
# back to the frequency code's natural units.
#
# Trigger condition: when time_span > 1000 × n_obs, the axis is
# almost certainly in seconds (no time grid has mean interval > 1000
# in natural units). Below that threshold, assume integer/index units.
_SECONDS_PER_UNIT = {
    "D": 86400.0,
    "B": 86400.0,
    "W": 86400.0 * 7,
    "M": 86400.0 * 30.4375,   # average month
    "MS": 86400.0 * 30.4375,
    "Q": 86400.0 * 91.3125,   # average quarter
    "QS": 86400.0 * 91.3125,
    "Y": 86400.0 * 365.25,
    "A": 86400.0 * 365.25,
}


def convert_period_to_native(period_raw, freq_code, n_obs=None, time_span=None):
    """Convert a Lomb-Scargle raw period to ``freq_code`` natural units.

    Returns ``(period_native, units_label)`` where units_label is
    "observations" when the wrapper's time axis was integer-indexed,
    or the short frequency code (M/Q/D/Y) when the wrapper's axis was
    seconds-scale and conversion applied.

    Heuristic: if ``time_span > 1000 × n_obs``, the time axis is in
    seconds; convert via the ``freq_code`` seconds-per-unit factor.
    Otherwise the axis is integer-indexed and the period is already
    in "observations" units.
    """
    try:
        p = float(period_raw)
    except Exception:
        return period_raw, "observations"
    if n_obs and time_span and time_span > 1000 * n_obs:
        # Seconds-scale axis — convert.
        factor = _SECONDS_PER_UNIT.get(str(freq_code or "").upper().strip())
        if factor and factor > 0:
            return p / factor, (freq_code or "").strip()
    return p, "observations"
