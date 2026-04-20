"""
GCC-PHAT (Generalized Cross-Correlation with Phase Transform) delay estimation
for Time Series Lab.

GCC-PHAT estimates the time delay between two signals by computing the
generalized cross-correlation with a phase-transform weighting function.
The PHAT weighting whitens the cross-spectrum, making the delay estimate
robust to noise and reverberation.

Method:
1. Compute cross-power spectrum: G_xy(f) = X(f) * conj(Y(f)).
2. Apply PHAT weighting: W(f) = 1 / |G_xy(f)|.
3. Inverse FFT to get the GCC-PHAT function.
4. The peak location gives the estimated delay.
"""

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)

_PRESET_CONFIG = {
    "Fast":     {"n_peaks": 3,  "interp_factor": 1,  "bootstrap": 0},
    "Balanced": {"n_peaks": 5,  "interp_factor": 4,  "bootstrap": 200},
    "Thorough": {"n_peaks": 10, "interp_factor": 16, "bootstrap": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Estimate delay between two series using GCC-PHAT.

    Requires 2 series.

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag to search (default: N//4).
    weighting : str, optional
        Weighting function: 'phat' (default), 'scot', 'roth', 'unfiltered'.
    fs : float, optional
        Sampling frequency for interpreting delay in time units (default: 1.0).
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        x_name, x_vals = all_series[0]
        y_name, y_vals = all_series[1]
        warnings = []

        if len(x_vals) != len(y_vals):
            return make_error_response(
                ctx,
                f"Series lengths differ: '{x_name}' has {len(x_vals)}, "
                f"'{y_name}' has {len(y_vals)}.",
                error_fixes=["Select two columns of the same length."],
            )

        x_clean, y_clean = dropna_aligned(x_vals, y_vals)
        n_dropped = len(x_vals) - len(x_clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to missing values.")

        n = len(x_clean)
        if n < 16:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. GCC-PHAT needs at least 16.",
                error_fixes=["Provide longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        max_lag_param = ctx.get_param("max_lag")
        max_lag = int(max_lag_param) if max_lag_param is not None else n // 4
        max_lag = min(max_lag, n - 1)

        weighting = ctx.get_param("weighting", "phat").lower()
        fs = float(ctx.get_param("fs", 1.0))
        interp_factor = cfg["interp_factor"]

        progress_callback("Computing GCC-PHAT", 20)

        # Zero-mean
        x = x_clean - np.mean(x_clean)
        y = y_clean - np.mean(y_clean)

        # FFT length (next power of 2 for efficiency, with zero-padding for interpolation)
        nfft = int(2 ** np.ceil(np.log2(2 * n - 1))) * interp_factor

        # Cross-power spectrum
        X = np.fft.rfft(x, n=nfft)
        Y = np.fft.rfft(y, n=nfft)
        Gxy = X * np.conj(Y)

        # Apply weighting
        if weighting == "phat":
            W = 1.0 / (np.abs(Gxy) + 1e-15)
        elif weighting == "scot":
            Gxx = X * np.conj(X)
            Gyy = Y * np.conj(Y)
            W = 1.0 / (np.sqrt(np.abs(Gxx) * np.abs(Gyy)) + 1e-15)
        elif weighting == "roth":
            Gxx = X * np.conj(X)
            W = 1.0 / (np.abs(Gxx) + 1e-15)
        else:  # unfiltered
            W = np.ones_like(Gxy, dtype=float)

        # GCC
        gcc = np.fft.irfft(Gxy * W, n=nfft)

        # Rearrange to center the zero lag
        gcc = np.fft.fftshift(gcc)
        center = nfft // 2

        # Lag axis (in samples, accounting for interpolation)
        lags_samples = (np.arange(nfft) - center) / interp_factor
        lags_time = lags_samples / fs

        # Restrict to max_lag
        lag_mask = np.abs(lags_samples) <= max_lag
        gcc_restricted = gcc[lag_mask]
        lags_restricted = lags_samples[lag_mask]
        lags_time_restricted = lags_time[lag_mask]

        progress_callback("Finding peaks", 50)

        # Find the primary peak
        peak_idx = np.argmax(gcc_restricted)
        estimated_delay_samples = float(lags_restricted[peak_idx])
        estimated_delay_time = float(lags_time_restricted[peak_idx])
        peak_value = float(gcc_restricted[peak_idx])

        # Find additional peaks
        n_peaks = cfg["n_peaks"]
        peak_indices = _find_peaks(gcc_restricted, n_peaks)
        peaks = []
        for pi in peak_indices:
            peaks.append({
                "delay_samples": float(lags_restricted[pi]),
                "delay_time": float(lags_time_restricted[pi]),
                "gcc_value": float(gcc_restricted[pi]),
            })

        progress_callback("Bootstrap confidence interval", 65)

        # Bootstrap CI for delay estimate
        delay_ci = [None, None]
        if cfg["bootstrap"] > 0:
            boot_delays = np.zeros(cfg["bootstrap"])
            block_size = max(1, n // 10)

            for b in range(cfg["bootstrap"]):
                # Block bootstrap to preserve some temporal structure
                n_blocks = int(np.ceil(n / block_size))
                block_starts = np.random.randint(0, n - block_size + 1, size=n_blocks)
                x_b = np.concatenate([x[s:s + block_size] for s in block_starts])[:n]
                y_b = np.concatenate([y[s:s + block_size] for s in block_starts])[:n]

                X_b = np.fft.rfft(x_b, n=nfft)
                Y_b = np.fft.rfft(y_b, n=nfft)
                Gxy_b = X_b * np.conj(Y_b)

                if weighting == "phat":
                    W_b = 1.0 / (np.abs(Gxy_b) + 1e-15)
                else:
                    W_b = np.ones_like(Gxy_b, dtype=float)

                gcc_b = np.fft.irfft(Gxy_b * W_b, n=nfft)
                gcc_b = np.fft.fftshift(gcc_b)
                gcc_b_r = gcc_b[lag_mask]
                pi_b = np.argmax(gcc_b_r)
                boot_delays[b] = lags_restricted[pi_b] / fs

            delay_ci = [
                round(float(np.percentile(boot_delays, 2.5)), 4),
                round(float(np.percentile(boot_delays, 97.5)), 4),
            ]

        progress_callback("Building output", 85)

        # Peaks table
        peak_rows = []
        for rank, p in enumerate(peaks):
            peak_rows.append([
                rank + 1,
                round(p["delay_samples"], 2),
                round(p["delay_time"], 4),
                round(p["gcc_value"], 6),
            ])

        peak_table = make_table(
            "GCC-PHAT Peaks",
            ["Rank", "Delay (samples)", "Delay (time)", "GCC Value"],
            peak_rows,
        )

        # Summary table
        summary_rows = [
            ["Estimated delay (samples)", round(estimated_delay_samples, 2)],
            ["Estimated delay (time)", round(estimated_delay_time, 4)],
            ["Peak GCC value", round(peak_value, 6)],
            ["Weighting", weighting.upper()],
            ["Sampling frequency (fs)", fs],
            ["Max lag (samples)", max_lag],
            ["Interpolation factor", interp_factor],
            ["FFT length", nfft],
            ["Observations", n],
        ]
        if delay_ci[0] is not None:
            summary_rows.append(["95% CI lower", delay_ci[0]])
            summary_rows.append(["95% CI upper", delay_ci[1]])

        summary_table = make_table("Summary", ["Metric", "Value"], summary_rows)

        # GCC function table (subsampled)
        max_display = 500
        step_gcc = max(1, len(gcc_restricted) // max_display)
        gcc_rows = []
        for i in range(0, len(gcc_restricted), step_gcc):
            gcc_rows.append([
                round(float(lags_restricted[i]), 2),
                round(float(lags_time_restricted[i]), 4),
                round(float(gcc_restricted[i]), 8),
            ])

        gcc_table = make_table(
            "GCC-PHAT Function",
            ["Lag (samples)", "Lag (time)", "GCC Value"],
            gcc_rows,
        )

        # Determine lead/lag direction
        if abs(estimated_delay_samples) < 0.5:
            direction = f"'{x_name}' and '{y_name}' are approximately synchronized"
        elif estimated_delay_samples > 0:
            direction = f"'{y_name}' leads '{x_name}' by {abs(estimated_delay_time):.3f} time units"
        else:
            direction = f"'{x_name}' leads '{y_name}' by {abs(estimated_delay_time):.3f} time units"

        # Peak sharpness (quality indicator)
        gcc_std = float(np.std(gcc_restricted))
        snr = peak_value / gcc_std if gcc_std > 0 else 0.0

        if snr > 5:
            quality = "high confidence"
        elif snr > 3:
            quality = "moderate confidence"
        else:
            quality = "low confidence"

        plain_english = (
            f"GCC-PHAT delay estimation between '{x_name}' and '{y_name}' "
            f"({n} observations). Estimated delay: {estimated_delay_time:.4f} time units "
            f"({estimated_delay_samples:.1f} samples). "
            f"{direction}. "
            f"Peak SNR = {snr:.2f} ({quality}). "
        )
        if delay_ci[0] is not None:
            plain_english += (
                f"95% bootstrap CI: [{delay_ci[0]:.4f}, {delay_ci[1]:.4f}] time units."
            )

        charting = (
            "Line chart of the GCC-PHAT function vs lag, with the peak marked. "
            "Include vertical dashed lines at the estimated delay and any secondary peaks. "
            "If bootstrap was used, shade the 95% CI region."
        )

        progress_callback("Done", 100)

        _ci_lo = delay_ci[0] if delay_ci and len(delay_ci) >= 2 else None
        _ci_hi = delay_ci[1] if delay_ci and len(delay_ci) >= 2 else None
        interp = build_interpretation("gcc_phat_delay", {
            "series_name_x": x_name,
            "series_name_y": y_name,
            "delay_time": float(estimated_delay_time),
            "delay_time_units": "seconds" if fs else "samples",
            "delay_samples": float(estimated_delay_samples),
            "snr": float(snr),
            "ci_lower": float(_ci_lo) if _ci_lo is not None else None,
            "ci_upper": float(_ci_hi) if _ci_hi is not None else None,
            "sample_rate_hz": float(fs) if fs else None,
            "weighting": weighting,
            "n_bootstrap": int(cfg["bootstrap"]) if cfg.get("bootstrap") else None,
        })
        return make_response(
            ctx,
            tables=[peak_table, summary_table, gcc_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "x_series": x_name,
                "y_series": y_name,
                "estimated_delay_samples": round(estimated_delay_samples, 2),
                "estimated_delay_time": round(estimated_delay_time, 4),
                "peak_gcc": round(peak_value, 6),
                "snr": round(snr, 2),
                "weighting": weighting,
                "max_lag": max_lag,
                "interp_factor": interp_factor,
                "fs": fs,
                "bootstrap_samples": cfg["bootstrap"],
                "delay_ci": delay_ci,
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"GCC-PHAT delay estimation failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Try a different weighting function (phat, scot, roth, unfiltered).",
                "Reduce max_lag if the series is short.",
            ],
        )


def _find_peaks(signal, n_peaks):
    """
    Find the top n_peaks peak locations in a 1D signal.
    Uses simple local maximum detection.
    """
    n = len(signal)
    if n < 3:
        return [np.argmax(signal)]

    # Find local maxima
    local_max = []
    for i in range(1, n - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            local_max.append((signal[i], i))

    # Also check endpoints
    if signal[0] > signal[1]:
        local_max.append((signal[0], 0))
    if signal[-1] > signal[-2]:
        local_max.append((signal[-1], n - 1))

    if not local_max:
        return [np.argmax(signal)]

    # Sort by value descending
    local_max.sort(reverse=True)

    # Return top n_peaks
    return [idx for _, idx in local_max[:n_peaks]]
