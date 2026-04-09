"""
Rolling window cross-correlation for time-varying lag detection, for Time Series Lab.

Computes the cross-correlation function (CCF) between two series within
a sliding window, tracking how the optimal lag and correlation strength
change over time. This reveals non-stationary lead/lag relationships.

At each window position, the standard CCF is computed and the lag with
the maximum absolute correlation is recorded.
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)

_PRESET_CONFIG = {
    "Fast":     {"default_window": 60,  "step": 5,  "max_lag_frac": 0.25},
    "Balanced": {"default_window": 120, "step": 1,  "max_lag_frac": 0.33},
    "Thorough": {"default_window": 120, "step": 1,  "max_lag_frac": 0.40},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute rolling cross-correlation between two series.

    Requires 2 series.

    Parameters (via ctx.params)
    ---------------------------
    window : int, optional
        Rolling window size (default depends on preset).
    max_lag : int, optional
        Maximum lag to compute (default: window * max_lag_frac).
    step : int, optional
        Step size between windows (default depends on preset).
    significance_level : float, optional
        Threshold for significance bands. Default: 0.05.
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

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        window = int(ctx.get_param("window", cfg["default_window"]))
        window = min(window, n - 1)
        step = int(ctx.get_param("step", cfg["step"]))
        significance = float(ctx.get_param("significance_level", 0.05))

        max_lag_param = ctx.get_param("max_lag")
        if max_lag_param is not None:
            max_lag = int(max_lag_param)
        else:
            max_lag = max(1, int(window * cfg["max_lag_frac"]))

        if window < 20:
            return make_error_response(
                ctx,
                f"Window size ({window}) is too small. Need at least 20.",
                error_fixes=["Increase the window parameter or provide more data."],
            )

        if n < window + 10:
            return make_error_response(
                ctx,
                f"Only {n} valid observations with window={window}. Need at least window + 10.",
                error_fixes=["Provide longer series or reduce window size."],
            )

        progress_callback("Computing rolling cross-correlations", 15)

        # Rolling windows
        window_starts = list(range(0, n - window + 1, step))
        n_windows = len(window_starts)

        # Results storage
        optimal_lags = np.zeros(n_windows)
        optimal_ccfs = np.zeros(n_windows)
        center_times = np.zeros(n_windows, dtype=int)
        lag_stability = np.zeros(n_windows)  # std of CCF around peak

        # Full CCF matrix (windows x lags)
        n_lags_total = 2 * max_lag + 1
        ccf_matrix = np.zeros((n_windows, n_lags_total))

        # Bartlett significance band per window
        bartlett_band = 1.96 / np.sqrt(window)  # approximate for 95%
        from scipy.stats import norm
        z = norm.ppf(1.0 - significance / 2.0)
        bartlett_band = z / np.sqrt(window)

        for w_idx, w_start in enumerate(window_starts):
            pct = 15 + int(70 * w_idx / n_windows)
            if w_idx % max(1, n_windows // 20) == 0:
                progress_callback(f"Window {w_idx + 1}/{n_windows}", pct)

            w_end = w_start + window
            x_w = x_clean[w_start:w_end]
            y_w = y_clean[w_start:w_end]

            center_times[w_idx] = w_start + window // 2

            # Compute CCF for lags -max_lag to +max_lag
            x_dm = x_w - np.mean(x_w)
            y_dm = y_w - np.mean(y_w)
            denom = np.sqrt(np.sum(x_dm ** 2) * np.sum(y_dm ** 2))

            if denom < 1e-15:
                ccf_matrix[w_idx, :] = 0
                optimal_lags[w_idx] = 0
                optimal_ccfs[w_idx] = 0
                continue

            best_lag = 0
            best_abs_ccf = 0
            best_ccf_val = 0

            for lag_idx, lag in enumerate(range(-max_lag, max_lag + 1)):
                if lag >= 0:
                    # x leads y (positive lag)
                    ccf_val = np.sum(x_dm[:window - lag] * y_dm[lag:]) / denom if lag < window else 0
                else:
                    # y leads x (negative lag)
                    alag = -lag
                    ccf_val = np.sum(x_dm[alag:] * y_dm[:window - alag]) / denom if alag < window else 0

                ccf_matrix[w_idx, lag_idx] = ccf_val

                if abs(ccf_val) > best_abs_ccf:
                    best_abs_ccf = abs(ccf_val)
                    best_ccf_val = ccf_val
                    best_lag = lag

            optimal_lags[w_idx] = best_lag
            optimal_ccfs[w_idx] = best_ccf_val

            # Lag stability: how peaked is the CCF?
            ccf_abs = np.abs(ccf_matrix[w_idx, :])
            if np.max(ccf_abs) > 0:
                lag_stability[w_idx] = np.max(ccf_abs) - np.mean(ccf_abs)

        progress_callback("Computing summary statistics", 87)

        # Time column
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else None

        # Rolling results table
        rolling_rows = []
        for w_idx in range(n_windows):
            cidx = center_times[w_idx]
            t_label = time_col[cidx] if time_col else int(cidx + 1)
            is_sig = abs(optimal_ccfs[w_idx]) > bartlett_band

            rolling_rows.append([
                t_label,
                int(optimal_lags[w_idx]),
                round(float(optimal_ccfs[w_idx]), 6),
                round(float(lag_stability[w_idx]), 4),
                "Yes" if is_sig else "No",
            ])

        rolling_table = make_table(
            "Rolling Optimal Lag",
            ["Center Time", "Optimal Lag", "CCF at Lag", "Peak Sharpness", "Significant"],
            rolling_rows,
        )

        # Lag distribution analysis
        sig_mask = np.abs(optimal_ccfs) > bartlett_band
        sig_lags = optimal_lags[sig_mask]

        lag_dist_rows = []
        if len(sig_lags) > 0:
            unique_lags, counts = np.unique(sig_lags.astype(int), return_counts=True)
            sorted_idx = np.argsort(-counts)
            for i in sorted_idx[:min(15, len(sorted_idx))]:
                lag = int(unique_lags[i])
                cnt = int(counts[i])
                pct = 100 * cnt / len(sig_lags)
                mean_ccf = float(np.mean(optimal_ccfs[sig_mask & (optimal_lags == lag)]))
                lag_dist_rows.append([
                    lag,
                    cnt,
                    round(pct, 1),
                    round(mean_ccf, 4),
                ])

        lag_dist_table = make_table(
            "Lag Distribution (significant windows)",
            ["Lag", "Count", "% of Windows", "Mean CCF"],
            lag_dist_rows,
        )

        # Summary statistics
        mean_lag = float(np.mean(optimal_lags))
        std_lag = float(np.std(optimal_lags))
        median_lag = float(np.median(optimal_lags))
        mean_ccf = float(np.mean(np.abs(optimal_ccfs)))
        pct_significant = float(100 * np.mean(sig_mask))

        # Is the lag stable or time-varying?
        lag_cv = std_lag / abs(mean_lag) if abs(mean_lag) > 0.5 else std_lag
        if lag_cv < 0.5 and std_lag < 2:
            stability_desc = "stable"
        elif lag_cv < 1.5:
            stability_desc = "moderately varying"
        else:
            stability_desc = "highly variable"

        stats_rows = [
            ["Window size", window],
            ["Step size", step],
            ["Max lag", max_lag],
            ["N windows", n_windows],
            ["Mean optimal lag", round(mean_lag, 2)],
            ["Median optimal lag", round(median_lag, 1)],
            ["Std of optimal lag", round(std_lag, 2)],
            ["Mean |CCF|", round(mean_ccf, 4)],
            ["% significant windows", round(pct_significant, 1)],
            ["Bartlett band (95%)", round(bartlett_band, 4)],
            ["Lag stability", stability_desc],
        ]
        stats_table = make_table("Summary Statistics", ["Metric", "Value"], stats_rows)

        # CCF heatmap data (subsampled)
        max_heat_rows = 200
        heat_step = max(1, n_windows // max_heat_rows)
        heat_rows = []
        for w_idx in range(0, n_windows, heat_step):
            cidx = center_times[w_idx]
            t_label = time_col[cidx] if time_col else int(cidx + 1)
            row = [t_label]
            for lag_idx in range(n_lags_total):
                row.append(round(float(ccf_matrix[w_idx, lag_idx]), 4))
            heat_rows.append(row)

        heat_cols = ["Center Time"] + [str(lag) for lag in range(-max_lag, max_lag + 1)]
        heat_table = make_table("CCF Heatmap Data", heat_cols, heat_rows)

        # Plain English
        if pct_significant < 10:
            plain_english = (
                f"Rolling cross-correlation between '{x_name}' and '{y_name}' "
                f"({n} observations, window={window}). "
                f"Very few windows ({pct_significant:.0f}%) show significant correlation. "
                "The series do not appear to have a consistent lead/lag relationship."
            )
        else:
            # Most common significant lag
            if len(lag_dist_rows) > 0:
                most_common_lag = lag_dist_rows[0][0]
                most_common_pct = lag_dist_rows[0][2]
            else:
                most_common_lag = int(median_lag)
                most_common_pct = 0

            if most_common_lag > 0:
                lead_desc = f"'{x_name}' typically leads '{y_name}' by {most_common_lag} period(s)"
            elif most_common_lag < 0:
                lead_desc = f"'{y_name}' typically leads '{x_name}' by {abs(most_common_lag)} period(s)"
            else:
                lead_desc = "The series are typically contemporaneously correlated"

            plain_english = (
                f"Rolling cross-correlation between '{x_name}' and '{y_name}' "
                f"({n} observations, window={window}). "
                f"{lead_desc} (in {most_common_pct:.0f}% of significant windows). "
                f"The lag relationship is {stability_desc} over time "
                f"(std={std_lag:.1f}). "
                f"{pct_significant:.0f}% of windows show significant correlation."
            )

        charting = (
            "Three-panel chart: (1) Heat map of CCF values over time and lag, "
            "(2) Time series of the optimal lag with significance band, "
            "(3) Time series of the CCF at the optimal lag with significance threshold. "
            "Use a colorbar for the heatmap (blue=negative, red=positive correlation)."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[rolling_table, lag_dist_table, stats_table, heat_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "x_series": x_name,
                "y_series": y_name,
                "window": window,
                "step": step,
                "max_lag": max_lag,
                "n_windows": n_windows,
                "mean_lag": round(mean_lag, 2),
                "median_lag": round(median_lag, 1),
                "std_lag": round(std_lag, 2),
                "mean_abs_ccf": round(mean_ccf, 4),
                "pct_significant": round(pct_significant, 1),
                "lag_stability": stability_desc,
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Rolling CCF analysis failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Reduce window size if the series is short.",
                "Increase step size for faster computation.",
            ],
        )
