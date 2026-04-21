"""
Periodogram spectral density estimation for Time Series Lab.

Computes the periodogram (raw spectral density estimate) of a time series
using scipy.signal.periodogram. Optionally applies windowing and identifies
dominant frequencies / periodicities.

The periodogram estimates the power spectral density S(f), showing how
variance is distributed across frequencies.
"""

import numpy as np
from scipy.signal import periodogram as sp_periodogram, get_window

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)

_PRESET_CONFIG = {
    "Fast":     {"n_top_freqs": 5,  "detrend": "constant", "window": "boxcar"},
    "Balanced": {"n_top_freqs": 10, "detrend": "linear",   "window": "hann"},
    "Thorough": {"n_top_freqs": 20, "detrend": "linear",   "window": "hann"},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute and analyze the periodogram spectral density.

    Parameters (via ctx.params)
    ---------------------------
    window : str, optional
        Window function ('boxcar', 'hann', 'hamming', 'blackman', 'bartlett').
        Default depends on preset.
    detrend : str, optional
        Detrending method: 'constant' (remove mean), 'linear' (remove trend),
        or False (no detrending). Default depends on preset.
    fs : float, optional
        Sampling frequency. Default 1.0 (normalized).
    n_top_freqs : int, optional
        Number of dominant frequencies to report.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN
        clean = values[~np.isnan(values)]
        n_dropped = len(values) - len(clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(clean)
        if n < 16:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. Periodogram needs at least 16.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        window = ctx.get_param("window", cfg["window"])
        detrend_param = ctx.get_param("detrend", cfg["detrend"])
        fs = float(ctx.get_param("fs", 1.0))
        n_top = int(ctx.get_param("n_top_freqs", cfg["n_top_freqs"]))

        # Handle detrend parameter
        if detrend_param is False or detrend_param == "False" or detrend_param == "false":
            detrend_val = False
        else:
            detrend_val = str(detrend_param)

        progress_callback("Computing periodogram", 25)

        freqs, psd = sp_periodogram(
            clean,
            fs=fs,
            window=window,
            detrend=detrend_val,
            scaling="density",
        )

        # Also compute with 'spectrum' scaling for total power
        _, psd_spectrum = sp_periodogram(
            clean,
            fs=fs,
            window=window,
            detrend=detrend_val,
            scaling="spectrum",
        )

        progress_callback("Identifying dominant frequencies", 50)

        # Skip DC component (freq = 0)
        if len(freqs) > 1:
            freqs_ndc = freqs[1:]
            psd_ndc = psd[1:]
            psd_spec_ndc = psd_spectrum[1:]
        else:
            freqs_ndc = freqs
            psd_ndc = psd
            psd_spec_ndc = psd_spectrum

        # Find top frequencies by power
        if len(psd_ndc) > 0:
            top_indices = np.argsort(psd_ndc)[::-1][:n_top]
            total_power = float(np.sum(psd_ndc))
        else:
            top_indices = []
            total_power = 0.0

        # Top frequencies table
        top_rows = []
        for rank, idx in enumerate(top_indices):
            freq = float(freqs_ndc[idx])
            power = float(psd_ndc[idx])
            pct_power = 100 * power / total_power if total_power > 0 else 0.0

            # Convert frequency to period
            period = 1.0 / freq if freq > 0 else np.inf

            top_rows.append([
                rank + 1,
                round(freq, 6),
                round(period, 2) if np.isfinite(period) else "Inf",
                round(power, 6),
                round(pct_power, 2),
            ])

        top_table = make_table(
            "Dominant Frequencies",
            ["Rank", "Frequency", "Period", "Power (density)", "% Total Power"],
            top_rows,
        )

        progress_callback("Computing spectral statistics", 65)

        # Spectral statistics
        if len(psd_ndc) > 0 and total_power > 0:
            # Spectral entropy (normalized)
            psd_norm = psd_ndc / total_power
            psd_norm = psd_norm[psd_norm > 0]
            spectral_entropy = -np.sum(psd_norm * np.log(psd_norm)) / np.log(len(psd_norm)) \
                if len(psd_norm) > 1 else 0.0

            # Spectral centroid (mean frequency weighted by power)
            spectral_centroid = float(np.sum(freqs_ndc * psd_ndc) / total_power)

            # Spectral bandwidth
            spectral_bandwidth = float(
                np.sqrt(np.sum((freqs_ndc - spectral_centroid) ** 2 * psd_ndc) / total_power)
            )

            # Spectral edge frequency (frequency below which 95% power is contained)
            cumpower = np.cumsum(psd_ndc)
            edge_idx = np.searchsorted(cumpower, 0.95 * total_power)
            spectral_edge = float(freqs_ndc[min(edge_idx, len(freqs_ndc) - 1)])
        else:
            spectral_entropy = 0.0
            spectral_centroid = 0.0
            spectral_bandwidth = 0.0
            spectral_edge = 0.0

        stats_rows = [
            ["Total power", round(total_power, 6)],
            ["Spectral entropy (normalized)", round(spectral_entropy, 6)],
            ["Spectral centroid (mean freq)", round(spectral_centroid, 6)],
            ["Spectral bandwidth", round(spectral_bandwidth, 6)],
            ["Spectral edge (95%)", round(spectral_edge, 6)],
            ["N frequency bins", len(freqs)],
            ["Frequency resolution", round(float(fs / n), 6)],
            ["Nyquist frequency", round(float(fs / 2), 6)],
            ["Window", window],
            ["Detrend", str(detrend_val)],
        ]
        stats_table = make_table("Spectral Statistics", ["Metric", "Value"], stats_rows)

        progress_callback("Building periodogram table", 80)

        # Full periodogram table (subsample if very long)
        max_rows = 500
        step = max(1, len(freqs) // max_rows)
        psd_rows = []
        for i in range(0, len(freqs), step):
            period = 1.0 / freqs[i] if freqs[i] > 0 else None
            psd_rows.append([
                round(float(freqs[i]), 6),
                round(period, 2) if period is not None and np.isfinite(period) else None,
                round(float(psd[i]), 8),
                round(10 * np.log10(max(psd[i], 1e-20)), 2),  # dB scale
            ])

        psd_table = make_table(
            "Periodogram",
            ["Frequency", "Period", "Power Density", "Power (dB)"],
            psd_rows,
        )

        # Plain English summary
        if len(top_rows) > 0:
            dom_freq = top_rows[0][1]
            dom_period = top_rows[0][2]
            dom_pct = top_rows[0][4]

            plain_english = (
                f"Periodogram analysis of '{name}' ({n} observations). "
                f"Dominant frequency: {dom_freq} (period = {dom_period}), "
                f"accounting for {dom_pct}% of total spectral power. "
            )

            if spectral_entropy > 0.8:
                plain_english += (
                    f"Spectral entropy is high ({spectral_entropy:.3f}), "
                    "indicating a broadband signal with no single dominant cycle. "
                )
            elif spectral_entropy < 0.4:
                plain_english += (
                    f"Spectral entropy is low ({spectral_entropy:.3f}), "
                    "indicating concentrated power at specific frequencies (periodic signal). "
                )
            else:
                plain_english += (
                    f"Spectral entropy is moderate ({spectral_entropy:.3f}). "
                )

            if len(top_rows) >= 2:
                second_freq = top_rows[1][1]
                second_period = top_rows[1][2]
                plain_english += (
                    f"Second strongest frequency: {second_freq} (period = {second_period})."
                )
        else:
            plain_english = f"Periodogram computed for '{name}' ({n} observations) but no dominant frequencies identified."

        charting = (
            "Line chart of power spectral density vs frequency (linear scale), "
            "with optional log-log variant. Mark dominant frequencies with vertical dashed lines. "
            "Optionally include a secondary plot showing cumulative spectral power."
        )

        progress_callback("Done", 100)

        # Prompt C4 additions: dominant peak share, Nyquist, frequency
        # resolution, estimator variant disclosure.
        nyquist_freq = float(fs) / 2.0
        freq_resolution = float(fs) / max(n, 1)
        top1_pct = float(top_rows[0][4]) if top_rows else None

        audit = {
            "window": window,
            "detrend": str(detrend_val),
            "fs": fs,
            "n_obs": n,
            "n_freq_bins": len(freqs),
            "total_power": round(total_power, 6),
            "spectral_entropy": round(spectral_entropy, 6),
            "spectral_centroid": round(spectral_centroid, 6),
            "spectral_bandwidth": round(spectral_bandwidth, 6),
            "spectral_edge_95": round(spectral_edge, 6),
            "nyquist_frequency": nyquist_freq,
            "frequency_resolution": freq_resolution,
            "estimator_variant": "raw",
            "top_peak_power_pct": top1_pct,
            "dominant_frequency": round(float(top_rows[0][1]), 6) if top_rows else None,
            "dominant_period": top_rows[0][2] if top_rows else None,
        }

        # Prompt C4 interpretation layer wire-in.
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        _interp_dict["series_name"] = name
        interp = build_interpretation("periodogram_spectral_density", _interp_dict)

        return make_response(
            ctx,
            tables=[top_table, stats_table, psd_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Periodogram computation failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with no text values.",
                "Try a different window function (e.g., 'hann', 'boxcar').",
                "Check for constant or near-constant series.",
            ],
        )
