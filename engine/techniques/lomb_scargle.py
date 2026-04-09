"""
Lomb-Scargle periodogram for irregularly sampled time series, for Time Series Lab.

The Lomb-Scargle periodogram extends classical spectral analysis to
unevenly spaced data. It fits sinusoids at each trial frequency and reports
the normalized power, making it ideal for detecting periodic signals in
data with gaps or irregular sampling.

Uses scipy.signal.lombscargle for the core computation.
"""

import numpy as np
from scipy.signal import lombscargle
from scipy.stats import expon as sp_expon

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)

_PRESET_CONFIG = {
    "Fast":     {"oversampling": 2,  "n_top_freqs": 5,  "false_alarm_method": "baluev"},
    "Balanced": {"oversampling": 5,  "n_top_freqs": 10, "false_alarm_method": "baluev"},
    "Thorough": {"oversampling": 10, "n_top_freqs": 20, "false_alarm_method": "bootstrap"},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute the Lomb-Scargle periodogram.

    Requires: at least 1 series. Time column is used as observation times.
    If no time column is provided, uses integer indices (but the LS method
    is most useful with irregular times).

    Parameters (via ctx.params)
    ---------------------------
    min_freq : float, optional
        Minimum angular frequency to evaluate. Default: 2*pi / (T_max - T_min).
    max_freq : float, optional
        Maximum angular frequency. Default: pi * N / (T_max - T_min) (Nyquist-like).
    oversampling : int, optional
        Oversampling factor for frequency grid. Default depends on preset.
    n_top_freqs : int, optional
        Number of top frequencies to report.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Parse time column to numeric
        if ctx.time and len(ctx.time) == len(values):
            t_numeric = _parse_times(ctx.time)
            if t_numeric is None:
                warnings.append(
                    "Could not parse time column to numeric. Using integer indices. "
                    "Lomb-Scargle is most useful with actual timestamps."
                )
                t_numeric = np.arange(len(values), dtype=float)
        else:
            t_numeric = np.arange(len(values), dtype=float)
            if not ctx.time:
                warnings.append("No time column provided. Using integer indices.")

        # Drop NaN (keeping alignment between t and y)
        valid = ~np.isnan(values) & ~np.isnan(t_numeric)
        t = t_numeric[valid]
        y = values[valid]

        n_dropped = int((~valid).sum())
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(y)
        if n < 10:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. Lomb-Scargle needs at least 10.",
                error_fixes=["Provide a longer series."],
            )

        # Check for irregular spacing
        dt = np.diff(t)
        dt_std = np.std(dt) / np.mean(dt) if np.mean(dt) > 0 else 0
        if dt_std < 0.01:
            warnings.append(
                "Data appears regularly sampled. Lomb-Scargle works, but a standard "
                "periodogram may be more efficient for evenly spaced data."
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        oversampling = int(ctx.get_param("oversampling", cfg["oversampling"]))
        n_top = int(ctx.get_param("n_top_freqs", cfg["n_top_freqs"]))

        progress_callback("Setting up frequency grid", 15)

        T_span = t[-1] - t[0]
        if T_span <= 0:
            return make_error_response(
                ctx,
                "Time span is zero. Cannot compute Lomb-Scargle periodogram.",
                error_fixes=["Ensure the time column has varying values."],
            )

        # Frequency grid (angular frequencies)
        min_freq_param = ctx.get_param("min_freq")
        max_freq_param = ctx.get_param("max_freq")

        if min_freq_param is not None:
            omega_min = float(min_freq_param)
        else:
            omega_min = 2 * np.pi / T_span

        if max_freq_param is not None:
            omega_max = float(max_freq_param)
        else:
            omega_max = np.pi * n / T_span

        n_freqs = int(oversampling * n)
        angular_freqs = np.linspace(omega_min, omega_max, n_freqs)

        progress_callback("Computing Lomb-Scargle periodogram", 30)

        # Demean the data
        y_demean = y - np.mean(y)

        # scipy.signal.lombscargle expects angular frequencies
        power = lombscargle(t, y_demean, angular_freqs, normalize=True)

        # Convert angular frequencies to ordinary frequencies and periods
        ordinary_freqs = angular_freqs / (2 * np.pi)
        periods = 1.0 / ordinary_freqs

        progress_callback("Identifying dominant frequencies", 60)

        # Find top peaks
        top_indices = np.argsort(power)[::-1][:n_top]

        # False alarm probability (FAP) using Baluev (2008) approximation
        # For a normalized Lomb-Scargle, the FAP for power z is approximately:
        # FAP(z) ~ 1 - (1 - exp(-z))^M, where M ~ n_freqs (effective independent frequencies)
        M_eff = n_freqs  # conservative estimate
        fap_levels = [0.01, 0.05, 0.1]
        fap_power_thresholds = {}
        for fap in fap_levels:
            # Invert: z such that 1 - (1-exp(-z))^M = fap
            # => (1-exp(-z))^M = 1 - fap
            # => 1-exp(-z) = (1-fap)^(1/M)
            # => z = -ln(1 - (1-fap)^(1/M))
            inner = (1 - fap) ** (1.0 / M_eff)
            if inner < 1:
                z_thresh = -np.log(1 - inner)
            else:
                z_thresh = np.inf
            fap_power_thresholds[fap] = z_thresh

        # Bootstrap FAP for Thorough preset
        if cfg["false_alarm_method"] == "bootstrap":
            progress_callback("Bootstrap false alarm estimation", 70)
            n_boot = 1000
            max_powers_boot = np.zeros(n_boot)
            for b in range(n_boot):
                y_shuffle = np.random.permutation(y_demean)
                power_b = lombscargle(t, y_shuffle, angular_freqs, normalize=True)
                max_powers_boot[b] = np.max(power_b)

            for fap in fap_levels:
                boot_thresh = float(np.percentile(max_powers_boot, (1 - fap) * 100))
                fap_power_thresholds[fap] = boot_thresh

        # Top frequencies table
        top_rows = []
        total_power = float(np.sum(power))
        for rank, idx in enumerate(top_indices):
            freq_val = float(ordinary_freqs[idx])
            period_val = float(periods[idx])
            power_val = float(power[idx])
            pct = 100 * power_val / total_power if total_power > 0 else 0.0

            # FAP for this peak
            if power_val > fap_power_thresholds.get(0.01, np.inf):
                fap_label = "< 1%"
            elif power_val > fap_power_thresholds.get(0.05, np.inf):
                fap_label = "< 5%"
            elif power_val > fap_power_thresholds.get(0.1, np.inf):
                fap_label = "< 10%"
            else:
                fap_label = "> 10%"

            top_rows.append([
                rank + 1,
                round(freq_val, 6),
                round(period_val, 2),
                round(power_val, 6),
                round(pct, 2),
                fap_label,
            ])

        top_table = make_table(
            "Dominant Frequencies",
            ["Rank", "Frequency", "Period", "LS Power", "% Power", "FAP"],
            top_rows,
        )

        # FAP thresholds table
        fap_rows = []
        for fap in fap_levels:
            fap_rows.append([
                f"{fap*100:.0f}%",
                round(fap_power_thresholds[fap], 6),
            ])
        fap_table = make_table(
            "False Alarm Probability Thresholds",
            ["FAP Level", "Power Threshold"],
            fap_rows,
        )

        progress_callback("Building periodogram table", 80)

        # Full periodogram (subsampled for large outputs)
        max_rows = 500
        step = max(1, len(angular_freqs) // max_rows)
        psd_rows = []
        for i in range(0, len(angular_freqs), step):
            psd_rows.append([
                round(float(ordinary_freqs[i]), 6),
                round(float(periods[i]), 2),
                round(float(power[i]), 8),
            ])

        psd_table = make_table(
            "Lomb-Scargle Periodogram",
            ["Frequency", "Period", "Normalized Power"],
            psd_rows,
        )

        # Summary statistics
        stats_rows = [
            ["Observations", n],
            ["Time span", round(float(T_span), 4)],
            ["Mean sampling interval", round(float(np.mean(dt)), 4)],
            ["Sampling irregularity (CV)", round(float(dt_std), 4)],
            ["Frequency bins", n_freqs],
            ["Oversampling factor", oversampling],
            ["Max LS power", round(float(np.max(power)), 6)],
            ["FAP method", cfg["false_alarm_method"]],
        ]
        stats_table = make_table("Analysis Summary", ["Metric", "Value"], stats_rows)

        # Plain English
        if len(top_rows) > 0:
            dom_period = top_rows[0][2]
            dom_power = top_rows[0][3]
            dom_fap = top_rows[0][5]

            significant_peaks = sum(1 for r in top_rows if "1%" in r[5] or "5%" in r[5])

            plain_english = (
                f"Lomb-Scargle periodogram of '{name}' ({n} observations over "
                f"span {T_span:.2f}). Dominant period: {dom_period} "
                f"(power = {dom_power}, FAP {dom_fap}). "
            )

            if significant_peaks > 0:
                plain_english += (
                    f"{significant_peaks} significant periodic component(s) detected (FAP < 5%). "
                )
            else:
                plain_english += "No statistically significant periodic components detected. "

            if dt_std > 0.1:
                plain_english += (
                    f"The data is irregularly sampled (CV = {dt_std:.3f}), "
                    "making Lomb-Scargle the appropriate spectral method."
                )
        else:
            plain_english = f"Lomb-Scargle periodogram computed for '{name}' but no clear peaks found."

        charting = (
            "Line chart of Lomb-Scargle power vs frequency/period. "
            "Include horizontal dashed lines at FAP thresholds (1%, 5%, 10%). "
            "Mark significant peaks with vertical markers. "
            "Optionally show a dual x-axis (frequency and period)."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[top_table, fap_table, stats_table, psd_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "n_obs": n,
                "time_span": round(float(T_span), 4),
                "oversampling": oversampling,
                "n_freqs": n_freqs,
                "fap_method": cfg["false_alarm_method"],
                "max_power": round(float(np.max(power)), 6),
                "dominant_frequency": round(float(top_rows[0][1]), 6) if top_rows else None,
                "dominant_period": top_rows[0][2] if top_rows else None,
                "sampling_irregularity_cv": round(float(dt_std), 4),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Lomb-Scargle computation failed: {e}",
            error_fixes=[
                "Ensure the series and time column are numeric.",
                "Check for duplicate timestamps.",
                "For regularly sampled data, consider the standard periodogram instead.",
            ],
        )


def _parse_times(time_list):
    """
    Attempt to convert a list of time values to a numeric array.
    Tries: direct float conversion, then ISO date parsing.
    Returns None if parsing fails.
    """
    # Try direct numeric
    try:
        return np.array([float(t) for t in time_list], dtype=float)
    except (ValueError, TypeError):
        pass

    # Try ISO date parsing
    try:
        from datetime import datetime
        base = None
        nums = []
        for t in time_list:
            if isinstance(t, str):
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            else:
                nums.append(float(t))
                continue
            if base is None:
                base = dt
            nums.append((dt - base).total_seconds())
        return np.array(nums, dtype=float)
    except Exception:
        return None
