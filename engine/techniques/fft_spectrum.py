"""
FFT Spectral Analysis for Time Series Lab.

Computes the Fast Fourier Transform of a time series to identify dominant
periodicities/frequencies. Returns the power spectrum (periodogram),
dominant frequencies, and their corresponding periods.
"""

import numpy as np
from scipy.fft import fft, fftfreq

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _prepare_series(values):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([]), 0
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
        else:
            trimmed = trimmed[~np.isnan(trimmed)]
            nan_count = 0
    return trimmed, nan_count


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run FFT spectral analysis on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    detrend : str, optional
        'none' (no detrending), 'mean' (subtract mean, default),
        'linear' (subtract linear trend).
    window : str, optional
        Window function: 'none' (rectangular, default), 'hann', 'hamming',
        'blackman', 'bartlett'.
    n_top : int, optional
        Number of top peaks to report. Default 10.
    min_period : float, optional
        Minimum period (in observation units) to consider. Default 2.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 8:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. FFT needs at least 8.",
                error_fixes=["Provide a longer time series."],
            )

        detrend = ctx.get_param("detrend", "mean")
        window_type = ctx.get_param("window", "none").lower()
        n_top = int(ctx.get_param("n_top", 10))
        min_period = float(ctx.get_param("min_period", 2.0))

        progress_callback("Preprocessing", 10)

        # Detrend
        signal = clean.copy()
        if detrend == "mean":
            signal = signal - np.mean(signal)
        elif detrend == "linear":
            x = np.arange(n)
            coeffs = np.polyfit(x, signal, 1)
            signal = signal - np.polyval(coeffs, x)
        # else 'none' - no detrending

        # Apply window function
        if window_type == "hann":
            window = np.hanning(n)
        elif window_type == "hamming":
            window = np.hamming(n)
        elif window_type == "blackman":
            window = np.blackman(n)
        elif window_type == "bartlett":
            window = np.bartlett(n)
        else:
            window = np.ones(n)

        windowed = signal * window

        progress_callback("Computing FFT", 25)

        # Compute FFT
        yf = fft(windowed)
        xf = fftfreq(n, d=1.0)  # d=1 means frequencies in cycles per observation

        # One-sided spectrum (positive frequencies only)
        pos_mask = xf > 0
        freqs = xf[pos_mask]
        amplitudes = np.abs(yf[pos_mask]) * 2.0 / n  # normalize
        power = amplitudes ** 2  # power spectrum

        # Filter by min_period
        max_freq = 1.0 / min_period if min_period > 0 else np.inf
        freq_mask = freqs <= max_freq
        freqs = freqs[freq_mask]
        amplitudes = amplitudes[freq_mask]
        power = power[freq_mask]

        if len(freqs) == 0:
            return make_error_response(
                ctx,
                "No frequencies in the valid range after filtering.",
                error_fixes=["Reduce min_period or provide a longer series."],
            )

        # Compute periods
        periods = 1.0 / freqs

        progress_callback("Identifying peaks", 50)

        # Find peaks (local maxima in power)
        peak_indices = _find_peaks(power)

        # Sort peaks by power (descending)
        if len(peak_indices) > 0:
            sorted_peaks = sorted(peak_indices, key=lambda i: power[i], reverse=True)
        else:
            # No local maxima found; use top power values
            sorted_peaks = list(np.argsort(power)[::-1])

        top_peaks = sorted_peaks[:n_top]

        # Top peaks table
        peak_rows = []
        for rank, idx in enumerate(top_peaks):
            peak_rows.append([
                rank + 1,
                round(float(freqs[idx]), 6),
                round(float(periods[idx]), 2),
                round(float(amplitudes[idx]), 6),
                round(float(power[idx]), 6),
                round(float(power[idx] / np.sum(power) * 100), 2) if np.sum(power) > 0 else 0,
            ])

        peak_table = make_table(
            "Dominant Frequencies",
            ["Rank", "Frequency (cycles/obs)", "Period (obs)", "Amplitude", "Power", "Power %"],
            peak_rows,
        )

        # Full spectrum table (subsampled for large series)
        progress_callback("Building spectrum table", 70)
        n_freqs = len(freqs)
        step = max(1, n_freqs // 500) if ctx.preset == "Fast" else max(1, n_freqs // 1000)
        spec_rows = []
        for i in range(0, n_freqs, step):
            spec_rows.append([
                round(float(freqs[i]), 6),
                round(float(periods[i]), 2),
                round(float(amplitudes[i]), 6),
                round(float(power[i]), 6),
            ])
        spec_table = make_table(
            "Power Spectrum",
            ["Frequency", "Period", "Amplitude", "Power"],
            spec_rows,
        )

        # Diagnostics
        total_power = float(np.sum(power))
        top_power = sum(power[idx] for idx in top_peaks)
        top_pct = round(top_power / total_power * 100, 1) if total_power > 0 else 0

        diag_rows = [
            ["Series", name],
            ["Observations", n],
            ["Detrending", detrend],
            ["Window", window_type],
            ["Frequency Resolution", round(1.0 / n, 6)],
            ["Nyquist Frequency", round(0.5, 4)],
            ["Total Power", round(total_power, 6)],
            ["Top Peaks Power %", top_pct],
            ["Peaks Reported", len(top_peaks)],
        ]
        diag_table = make_table("Analysis Parameters", ["Metric", "Value"], diag_rows)

        # Plain English
        if len(top_peaks) > 0:
            dominant_period = periods[top_peaks[0]]
            dominant_pct = round(power[top_peaks[0]] / total_power * 100, 1) if total_power > 0 else 0
            plain = (
                f"FFT spectral analysis of '{name}' ({n} observations). "
                f"Dominant period: {dominant_period:.1f} observations "
                f"(frequency {freqs[top_peaks[0]]:.4f} cycles/obs), "
                f"accounting for {dominant_pct}% of total spectral power."
            )
            if len(top_peaks) > 1:
                second_period = periods[top_peaks[1]]
                plain += f" Second strongest period: {second_period:.1f} observations."

            # Interpret common periods
            interpretations = _interpret_period(dominant_period, ctx.frequency)
            if interpretations:
                plain += f" This likely corresponds to {interpretations}."
        else:
            plain = (
                f"FFT analysis of '{name}' ({n} observations) did not find clear "
                "dominant frequencies. The series may be aperiodic or dominated by noise."
            )

        charting = (
            "Line chart of the power spectrum (power vs. frequency or period). "
            "Mark the top peaks with labels showing their periods. "
            "Optional: log-scale y-axis for better visibility of weaker peaks."
        )

        progress_callback("Done", 100)

        # Prompt C4 additions: explicit sampling/Nyquist disclosure;
        # top-peak power share and top-N share for Tier 1 rendering.
        freq_resolution = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 1.0 / max(n, 1)
        nyquist_freq = float(np.max(freqs)) if len(freqs) > 0 else 0.5
        top1_pct = None
        if len(top_peaks) > 0 and total_power > 0:
            top1_pct = float(power[top_peaks[0]] / total_power * 100.0)

        audit = {
            "detrend": detrend,
            "window": window_type,
            "n_observations": n,
            "n_peaks_reported": len(top_peaks),
            "sampling_frequency": 1.0,  # cycles/obs normalized
            "nyquist_frequency": nyquist_freq,
            "frequency_resolution": freq_resolution,
            "total_power": round(total_power, 6),
            "top_peak_power_pct": round(top1_pct, 2) if top1_pct is not None else None,
            "top_peaks_power_pct": float(top_pct),
        }
        if len(top_peaks) > 0:
            audit["dominant_period"] = round(float(periods[top_peaks[0]]), 2)
            audit["dominant_frequency"] = round(float(freqs[top_peaks[0]]), 6)

        # Prompt C4 interpretation layer wire-in.
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        _interp_dict["series_name"] = name
        _interp_dict["n_obs"] = n
        interp = build_interpretation("fft_spectrum", _interp_dict)

        return make_response(
            ctx,
            tables=[peak_table, spec_table, diag_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"FFT spectral analysis failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Provide at least 8 observations.",
                "Try detrend='linear' if the series has a strong trend.",
                "Use a window function ('hann', 'hamming') to reduce spectral leakage.",
            ],
        )


def _find_peaks(arr):
    """Simple peak detection: find indices where arr[i] > arr[i-1] and arr[i] > arr[i+1]."""
    peaks = []
    for i in range(1, len(arr) - 1):
        if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
            peaks.append(i)
    return peaks


def _interpret_period(period, frequency):
    """Try to give a human-readable interpretation of a dominant period."""
    freq = (frequency or "").strip().upper()

    if freq == "D":
        if 6 <= period <= 8:
            return "a weekly cycle"
        elif 28 <= period <= 32:
            return "a monthly cycle"
        elif 360 <= period <= 370:
            return "an annual cycle"
    elif freq == "M" or freq == "MS":
        if 11 <= period <= 13:
            return "an annual cycle"
        elif 5 <= period <= 7:
            return "a semi-annual cycle"
        elif 2.5 <= period <= 3.5:
            return "a quarterly cycle"
    elif freq == "H":
        if 23 <= period <= 25:
            return "a daily cycle"
        elif 167 <= period <= 169:
            return "a weekly cycle"
    elif freq == "W":
        if 51 <= period <= 53:
            return "an annual cycle"
        elif 25 <= period <= 27:
            return "a semi-annual cycle"
    elif freq in ("Q", "QS"):
        if 3.5 <= period <= 4.5:
            return "an annual cycle"

    return None
