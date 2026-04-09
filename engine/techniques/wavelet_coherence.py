"""
Wavelet coherence and phase-lag analysis between two time series
for Time Series Lab.

Computes the continuous wavelet transform (CWT) of two series using PyWavelets,
then calculates wavelet coherence (analogous to squared correlation in
time-frequency space) and the phase difference (indicating lead/lag at each
scale and time).

The coherence measures how consistently the two series co-move at each
frequency (scale) over time, while the phase angle reveals which series leads.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)

_PRESET_CONFIG = {
    "Fast":     {"n_scales": 32,  "smoothing_width": 3},
    "Balanced": {"n_scales": 64,  "smoothing_width": 5},
    "Thorough": {"n_scales": 128, "smoothing_width": 7},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute wavelet coherence between two series.

    Requires 2 series.

    Parameters (via ctx.params)
    ---------------------------
    wavelet : str, optional
        Wavelet name for CWT (default 'morl' for Morlet).
    n_scales : int, optional
        Number of scales (default depends on preset).
    min_scale : float, optional
        Minimum scale (default 2).
    max_scale : float, optional
        Maximum scale (default N/4).
    smoothing_width : int, optional
        Width of the smoothing kernel for coherence estimation.
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
                f"'{y_name}' has {len(y_vals)}. They must be equal.",
                error_fixes=["Select two columns of the same length."],
            )

        x_clean, y_clean = dropna_aligned(x_vals, y_vals)
        n_dropped = len(x_vals) - len(x_clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to missing values.")

        n = len(x_clean)
        if n < 32:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. Wavelet coherence needs at least 32.",
                error_fixes=["Provide longer series for wavelet analysis."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        wavelet_name = ctx.get_param("wavelet", "morl")
        n_scales = int(ctx.get_param("n_scales", cfg["n_scales"]))
        min_scale = float(ctx.get_param("min_scale", 2))
        max_scale = float(ctx.get_param("max_scale", n / 4))
        smooth_w = int(ctx.get_param("smoothing_width", cfg["smoothing_width"]))

        # Import pywt
        try:
            import pywt
        except ImportError:
            return make_error_response(
                ctx,
                "PyWavelets (pywt) is not installed. Please install it: pip install PyWavelets",
                error_fixes=["Run: pip install PyWavelets"],
            )

        progress_callback("Computing continuous wavelet transforms", 20)

        # Create scales array (logarithmically spaced)
        scales = np.logspace(np.log10(min_scale), np.log10(max_scale), n_scales)

        # Standardize the series
        x_std = (x_clean - np.mean(x_clean)) / (np.std(x_clean) + 1e-10)
        y_std = (y_clean - np.mean(y_clean)) / (np.std(y_clean) + 1e-10)

        # CWT
        try:
            Wx, _ = pywt.cwt(x_std, scales, wavelet_name)
            Wy, _ = pywt.cwt(y_std, scales, wavelet_name)
        except Exception as cwt_err:
            return make_error_response(
                ctx,
                f"CWT computation failed: {cwt_err}",
                error_fixes=[
                    f"Try a different wavelet (current: '{wavelet_name}'). "
                    "Common choices: 'morl', 'cmor1.5-1.0', 'cgau1'.",
                ],
            )

        progress_callback("Computing wavelet coherence", 50)

        # Cross-wavelet spectrum
        Wxy = Wx * np.conj(Wy)

        # Smoothing for coherence estimation (time-direction Gaussian kernel)
        def smooth_time(W, width):
            """Gaussian smoothing along the time axis."""
            from scipy.ndimage import uniform_filter1d
            return uniform_filter1d(W.real, size=width, axis=1) + \
                   1j * uniform_filter1d(W.imag, size=width, axis=1)

        def smooth_scale(W, width):
            """Uniform smoothing along the scale axis."""
            from scipy.ndimage import uniform_filter1d
            return uniform_filter1d(W.real, size=max(width // 2, 1), axis=0) + \
                   1j * uniform_filter1d(W.imag, size=max(width // 2, 1), axis=0)

        # Smooth cross-spectrum and auto-spectra
        S_xy = smooth_scale(smooth_time(Wxy, smooth_w), smooth_w)
        S_xx = smooth_scale(smooth_time(np.abs(Wx) ** 2, smooth_w), smooth_w).real
        S_yy = smooth_scale(smooth_time(np.abs(Wy) ** 2, smooth_w), smooth_w).real

        # Wavelet coherence: |S_xy|^2 / (S_xx * S_yy)
        denom = S_xx * S_yy
        denom[denom < 1e-20] = 1e-20
        coherence = np.abs(S_xy) ** 2 / denom
        coherence = np.clip(coherence, 0, 1)

        # Phase difference
        phase = np.angle(S_xy)  # in radians

        progress_callback("Computing scale-averaged statistics", 70)

        # Convert scales to approximate periods/frequencies
        # For Morlet wavelet: period ~ 1.03 * scale
        if wavelet_name.startswith("morl") or wavelet_name.startswith("cmor"):
            period_factor = 1.03
        else:
            period_factor = 1.0
        periods = scales * period_factor

        # Scale-averaged coherence (mean over time at each scale)
        mean_coherence = np.mean(coherence, axis=1)
        # Scale-averaged phase
        mean_phase = np.zeros(n_scales)
        for s in range(n_scales):
            # Circular mean of phase
            mean_phase[s] = np.angle(np.mean(np.exp(1j * phase[s, :])))

        # Convert phase to lag (in time units): lag = phase / (2*pi) * period
        mean_lag = mean_phase / (2 * np.pi) * periods

        # Find scales with highest coherence
        top_scale_idx = np.argsort(mean_coherence)[::-1][:min(10, n_scales)]

        # Scale coherence table
        scale_rows = []
        for rank, idx in enumerate(top_scale_idx):
            phase_deg = float(np.degrees(mean_phase[idx]))
            lag_val = float(mean_lag[idx])
            if lag_val > 0:
                lead_desc = f"'{x_name}' leads by {abs(lag_val):.2f}"
            elif lag_val < 0:
                lead_desc = f"'{y_name}' leads by {abs(lag_val):.2f}"
            else:
                lead_desc = "In phase"

            scale_rows.append([
                rank + 1,
                round(float(scales[idx]), 2),
                round(float(periods[idx]), 2),
                round(float(mean_coherence[idx]), 4),
                round(phase_deg, 2),
                round(lag_val, 2),
                lead_desc,
            ])

        scale_table = make_table(
            "Coherence by Scale (Top 10)",
            ["Rank", "Scale", "Period", "Mean Coherence", "Phase (deg)", "Lag", "Lead/Lag"],
            scale_rows,
        )

        progress_callback("Building coherence matrix table", 80)

        # Time-averaged coherence profile
        profile_rows = []
        for s in range(n_scales):
            profile_rows.append([
                round(float(scales[s]), 2),
                round(float(periods[s]), 2),
                round(float(mean_coherence[s]), 4),
                round(float(np.degrees(mean_phase[s])), 2),
                round(float(mean_lag[s]), 2),
            ])

        profile_table = make_table(
            "Coherence Profile",
            ["Scale", "Period", "Mean Coherence", "Mean Phase (deg)", "Mean Lag"],
            profile_rows,
        )

        # Time-varying coherence at the most coherent scale
        best_scale_idx = top_scale_idx[0]
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else list(range(1, n + 1))
        if isinstance(time_col, list) and len(time_col) > n:
            time_col = time_col[:n]

        max_display = 300
        step = max(1, n // max_display)
        tv_rows = []
        for i in range(0, n, step):
            tv_rows.append([
                time_col[i],
                round(float(coherence[best_scale_idx, i]), 4),
                round(float(np.degrees(phase[best_scale_idx, i])), 2),
            ])

        tv_table = make_table(
            f"Time-Varying Coherence (scale={scales[best_scale_idx]:.1f}, "
            f"period={periods[best_scale_idx]:.1f})",
            ["Time", "Coherence", "Phase (deg)"],
            tv_rows,
        )

        # Global statistics
        global_coh = float(np.mean(coherence))
        max_coh = float(np.max(coherence))
        high_coh_pct = float(np.mean(coherence > 0.7) * 100)

        stats_rows = [
            ["Global mean coherence", round(global_coh, 4)],
            ["Maximum coherence", round(max_coh, 4)],
            ["% time-frequency with coherence > 0.7", round(high_coh_pct, 1)],
            ["Best scale", round(float(scales[best_scale_idx]), 2)],
            ["Best period", round(float(periods[best_scale_idx]), 2)],
            ["Wavelet", wavelet_name],
            ["N scales", n_scales],
            ["Smoothing width", smooth_w],
            ["Observations", n],
        ]
        stats_table = make_table("Summary Statistics", ["Metric", "Value"], stats_rows)

        # Plain English
        best_coh = float(mean_coherence[best_scale_idx])
        best_period = float(periods[best_scale_idx])
        best_lag_val = float(mean_lag[best_scale_idx])

        if best_coh > 0.7:
            coh_desc = "strong"
        elif best_coh > 0.4:
            coh_desc = "moderate"
        else:
            coh_desc = "weak"

        if abs(best_lag_val) < 0.5:
            lag_desc = "approximately in phase (synchronous)"
        elif best_lag_val > 0:
            lag_desc = f"'{x_name}' leads '{y_name}' by ~{abs(best_lag_val):.1f} time units"
        else:
            lag_desc = f"'{y_name}' leads '{x_name}' by ~{abs(best_lag_val):.1f} time units"

        plain_english = (
            f"Wavelet coherence analysis between '{x_name}' and '{y_name}' "
            f"({n} observations). Strongest coherence ({best_coh:.3f}, {coh_desc}) "
            f"at period {best_period:.1f}, where the series are {lag_desc}. "
            f"Overall, {high_coh_pct:.1f}% of the time-frequency plane shows "
            f"coherence above 0.7. Global mean coherence: {global_coh:.3f}."
        )

        charting = (
            "Heat map of wavelet coherence (time on x-axis, period/scale on y-axis, "
            "coherence as color 0-1). Overlay arrows showing phase relationship "
            "(right = in-phase, left = anti-phase, up = series 2 leads, down = series 1 leads). "
            "Include a side panel showing scale-averaged coherence profile."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[scale_table, stats_table, profile_table, tv_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "x_series": x_name,
                "y_series": y_name,
                "wavelet": wavelet_name,
                "n_scales": n_scales,
                "smoothing_width": smooth_w,
                "global_mean_coherence": round(global_coh, 4),
                "max_coherence": round(max_coh, 4),
                "best_scale": round(float(scales[best_scale_idx]), 2),
                "best_period": round(float(periods[best_scale_idx]), 2),
                "best_scale_coherence": round(best_coh, 4),
                "best_scale_lag": round(best_lag_val, 2),
                "high_coherence_pct": round(high_coh_pct, 1),
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Wavelet coherence analysis failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Install PyWavelets: pip install PyWavelets",
                "Try a different wavelet (e.g., 'morl', 'cmor1.5-1.0').",
                "Reduce n_scales if memory is an issue.",
            ],
        )
