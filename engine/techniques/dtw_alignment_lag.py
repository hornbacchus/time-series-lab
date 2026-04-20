"""
Dynamic Time Warping (DTW) alignment and time-varying lag estimation
for Time Series Lab.

Uses DTW to find the optimal alignment between two time series, allowing
for non-linear time distortions. The warping path reveals how the temporal
relationship varies: at each point, the local lag can be extracted.

Implements DTW from scratch using dynamic programming with configurable
window constraints (Sakoe-Chiba band or Itakura parallelogram).
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
    format_pairwise_summary,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"window_frac": 0.10, "subsample": 4},
    "Balanced": {"window_frac": 0.20, "subsample": 2},
    "Thorough": {"window_frac": 0.50, "subsample": 1},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    DTW alignment and time-varying lag analysis.

    Requires 2 series.

    Parameters (via ctx.params)
    ---------------------------
    window_frac : float, optional
        Sakoe-Chiba window as fraction of series length (default depends on preset).
    normalize : bool, optional
        Whether to z-normalize both series before DTW (default True).
    step_pattern : str, optional
        'symmetric2' (default) or 'symmetric1'.
        symmetric2 allows diagonal, horizontal, and vertical steps.
        symmetric1 only allows diagonal steps (no repeated indices).
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        warnings = []

        # F2 multi-series disclosure.
        if len(all_series) > 2:
            ignored = [s[0] for s in all_series[2:]]
            warnings.append(
                f"DTW is a pairwise alignment. Used '{all_series[0][0]}' and "
                f"'{all_series[1][0]}'; ignored {len(ignored)} additional "
                f"series: {', '.join(ignored)}."
            )

        x_name, x_vals = all_series[0]
        y_name, y_vals = all_series[1]

        if len(x_vals) != len(y_vals):
            # DTW can handle different lengths, but we'll note it
            warnings.append(
                f"Series have different lengths ({len(x_vals)} vs {len(y_vals)}). "
                "DTW will align them, but lag interpretation may be less intuitive."
            )

        # Drop NaN from each series independently
        x_clean = x_vals[~np.isnan(x_vals)]
        y_clean = y_vals[~np.isnan(y_vals)]

        nx = len(x_clean)
        ny = len(y_clean)

        if nx < 10 or ny < 10:
            return make_error_response(
                ctx,
                f"Series too short ({nx}, {ny}). DTW needs at least 10 observations each.",
                error_fixes=["Provide longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        window_frac = float(ctx.get_param("window_frac", cfg["window_frac"]))
        do_normalize = bool(ctx.get_param("normalize", True))
        step_pattern = ctx.get_param("step_pattern", "symmetric2")
        subsample = cfg["subsample"]

        # Subsample for large series
        if subsample > 1 and min(nx, ny) > 500:
            x_work = x_clean[::subsample]
            y_work = y_clean[::subsample]
            warnings.append(
                f"Series subsampled by factor {subsample} for computational efficiency "
                f"({nx} -> {len(x_work)}, {ny} -> {len(y_work)})."
            )
            scale_factor = subsample
        else:
            x_work = x_clean.copy()
            y_work = y_clean.copy()
            scale_factor = 1

        nxw = len(x_work)
        nyw = len(y_work)

        # Normalize
        if do_normalize:
            x_mu, x_sigma = np.mean(x_work), np.std(x_work)
            y_mu, y_sigma = np.mean(y_work), np.std(y_work)
            if x_sigma > 1e-10:
                x_work = (x_work - x_mu) / x_sigma
            if y_sigma > 1e-10:
                y_work = (y_work - y_mu) / y_sigma

        # Sakoe-Chiba window
        window_size = max(1, int(window_frac * max(nxw, nyw)))

        progress_callback("Computing DTW cost matrix", 20)

        # DTW computation
        dtw_dist, cost_matrix, path = _dtw(
            x_work, y_work, window_size, step_pattern, progress_callback
        )

        progress_callback("Analyzing warping path", 70)

        # Extract time-varying lag from the warping path
        path_x = np.array([p[0] for p in path]) * scale_factor
        path_y = np.array([p[1] for p in path]) * scale_factor
        path_lag = path_y - path_x  # positive = y is ahead of x

        # For each x index, find the corresponding y index (and lag)
        # When there are multiple matches, take the middle one
        x_to_y = {}
        for px, py in zip(path_x, path_y):
            px_int = int(px)
            if px_int not in x_to_y:
                x_to_y[px_int] = []
            x_to_y[px_int].append(int(py))

        local_lags = np.zeros(nx)
        for xi in range(nx):
            if xi in x_to_y:
                matches = x_to_y[xi]
                local_lags[xi] = np.mean(matches) - xi
            elif xi > 0:
                local_lags[xi] = local_lags[xi - 1]  # carry forward

        # Summary statistics of the warping
        mean_lag = float(np.mean(local_lags))
        std_lag = float(np.std(local_lags))
        max_lag = float(np.max(local_lags))
        min_lag = float(np.min(local_lags))
        median_lag = float(np.median(local_lags))

        # Warping path length ratio (measure of distortion)
        path_len = len(path)
        diag_len = max(nxw, nyw)
        distortion_ratio = path_len / diag_len

        # Normalized DTW distance
        dtw_normalized = dtw_dist / path_len if path_len > 0 else dtw_dist

        # Lag segments: identify regions of consistent lag
        lag_segments = _segment_lags(local_lags, threshold=2.0)

        progress_callback("Building output", 85)

        time_col = ctx.time if ctx.time and len(ctx.time) >= nx else None

        # Local lag time series table
        max_display = 500
        step_ts = max(1, nx // max_display)
        lag_rows = []
        for i in range(0, nx, step_ts):
            t_label = time_col[i] if time_col else int(i + 1)
            lag_rows.append([
                t_label,
                round(float(x_clean[i]), 6),
                round(float(y_clean[min(i, ny - 1)]), 6) if i < ny else None,
                round(float(local_lags[i]), 2),
            ])

        lag_table = make_table(
            "Time-Varying Lag (from DTW alignment)",
            ["Time (X index)", f"{x_name}", f"{y_name}", "Local Lag (Y - X)"],
            lag_rows,
        )

        # Warping path table (subsampled)
        path_step = max(1, path_len // max_display)
        wp_rows = []
        for i in range(0, path_len, path_step):
            wp_rows.append([
                int(path_x[i]),
                int(path_y[i]),
                round(float(path_lag[i]), 2),
            ])

        wp_table = make_table(
            "Warping Path",
            ["X Index", "Y Index", "Lag"],
            wp_rows,
        )

        # Lag segments table
        seg_rows = []
        for seg in lag_segments:
            t_start = time_col[seg["start"]] if time_col else seg["start"] + 1
            t_end = time_col[seg["end"] - 1] if time_col else seg["end"]
            seg_rows.append([
                t_start,
                t_end,
                seg["end"] - seg["start"],
                round(seg["mean_lag"], 2),
                round(seg["std_lag"], 2),
            ])

        seg_table = make_table(
            "Lag Segments",
            ["Start", "End", "Length", "Mean Lag", "Std Lag"],
            seg_rows,
        )

        # Summary table
        summary_rows = [
            ["DTW distance", round(float(dtw_dist), 4)],
            ["Normalized DTW distance", round(float(dtw_normalized), 6)],
            ["Path length", path_len],
            ["Distortion ratio", round(distortion_ratio, 3)],
            ["Mean local lag", round(mean_lag, 2)],
            ["Median local lag", round(median_lag, 2)],
            ["Std of local lag", round(std_lag, 2)],
            ["Min local lag", round(min_lag, 2)],
            ["Max local lag", round(max_lag, 2)],
            ["N segments", len(lag_segments)],
            ["Sakoe-Chiba window", window_size * scale_factor],
            ["Normalized", do_normalize],
            ["Step pattern", step_pattern],
            ["Series X length", nx],
            ["Series Y length", ny],
        ]
        summary_table = make_table("DTW Summary", ["Metric", "Value"], summary_rows)

        # Determine lag character
        if std_lag < 1.5:
            lag_desc = "approximately constant"
        elif std_lag < abs(mean_lag) * 0.5:
            lag_desc = "mildly varying"
        else:
            lag_desc = "strongly time-varying"

        # F2 (d)-form summary via format_pairwise_summary. DTW reports a
        # signed median lag and a distance magnitude. Sign comes from the
        # median lag (positive = y leads x by the DTW convention used in
        # the segmentation code); the "statistic" shown in the paired fact
        # is the normalized DTW distance (smaller = tighter alignment).
        if abs(median_lag) < 1:
            direction_verb = "aligns contemporaneously with"
            paired_sign = "+"
            paired_lag = 0
        elif median_lag > 0:
            direction_verb = "lags"  # y > x means x lagged = "x lags y"
            paired_sign = "+"
            paired_lag = int(round(median_lag))
        else:
            direction_verb = "leads"
            paired_sign = "-"
            paired_lag = int(round(median_lag))

        prefix = (f"DTW alignment of '{x_name}' and '{y_name}' "
                  f"({nx} and {ny} obs)")
        extra = (f"Normalized DTW distance {dtw_normalized:.4f} "
                 f"(lower = more similar), lag is {lag_desc} "
                 f"(std={std_lag:.1f}, range {min_lag:.1f} to {max_lag:.1f}). "
                 f"Path distortion ratio {distortion_ratio:.2f}.")
        plain_english = format_pairwise_summary(
            prefix, x_name, y_name,
            sign=paired_sign,
            magnitude=abs(median_lag),
            lag=paired_lag,
            lag_unit=" periods",
            direction_verb=direction_verb,
            stat_name="median lag",
            test_name="DTW path analysis (no null distribution)",
            ac_note="no significance test — distance-based diagnostic",
            extra=extra,
        )

        charting = (
            "Three-panel chart: (1) Both series plotted together with DTW alignment lines "
            "connecting matched points, (2) Local lag over time showing how the "
            "temporal relationship varies, (3) DTW cost matrix heatmap with the optimal "
            "warping path overlaid as a line."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("dtw_alignment_lag", {
            "series_name_x": x_name,
            "series_name_y": y_name,
            "dtw_normalized": float(dtw_normalized),
            "median_lag": float(median_lag),
            "lag_std": float(std_lag),
            "max_lag": float(max_lag),
            "n_x": int(nx),
            "n_y": int(ny),
            "sakoe_chiba_band": int(window_size),
            "path_length": int(path_len),
            "diag_length": int(diag_len),
            "distortion_ratio": float(distortion_ratio),
        })
        return make_response(
            ctx,
            tables=[summary_table, lag_table, seg_table, wp_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "x_series": x_name,
                "y_series": y_name,
                "pair_used": [x_name, y_name],
                "pairs_ignored": [s[0] for s in all_series[2:]],
                "dtw_distance": round(float(dtw_dist), 4),
                "dtw_normalized": round(float(dtw_normalized), 6),
                "mean_lag": round(mean_lag, 2),
                "median_lag": round(median_lag, 2),
                "std_lag": round(std_lag, 2),
                "min_lag": round(min_lag, 2),
                "max_lag": round(max_lag, 2),
                "distortion_ratio": round(distortion_ratio, 3),
                "path_length": path_len,
                "window_frac": window_frac,
                "normalized": do_normalize,
                "step_pattern": step_pattern,
                "n_segments": len(lag_segments),
                "nx": nx,
                "ny": ny,
                **format_significance_disclosure(
                    test_name="DTW path analysis (distance-based, no null)",
                    critical_value_formula=(
                        "none — DTW is a distance metric, not a hypothesis "
                        "test; no p-value or confidence band emitted"
                    ),
                    ac_corrected=False,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"DTW alignment failed: {e}",
            error_fixes=[
                "Ensure both series are numeric.",
                "For very long series, use the 'Fast' preset to enable subsampling.",
                "Increase window_frac if the lag is large.",
            ],
        )


def _dtw(x, y, window, step_pattern, progress_callback):
    """
    Compute DTW distance, cost matrix, and warping path.

    Parameters
    ----------
    x, y : ndarray
        Input sequences.
    window : int
        Sakoe-Chiba window width.
    step_pattern : str
        'symmetric1' or 'symmetric2'.
    progress_callback : callable

    Returns
    -------
    distance : float
    cost_matrix : ndarray
    path : list of (i, j) tuples
    """
    nx = len(x)
    ny = len(y)

    # Cost matrix (inf = forbidden)
    D = np.full((nx + 1, ny + 1), np.inf)
    D[0, 0] = 0.0

    # Accumulated cost
    for i in range(1, nx + 1):
        if i % max(1, nx // 10) == 0:
            pct = 20 + int(45 * i / nx)
            progress_callback(f"DTW row {i}/{nx}", pct)

        j_start = max(1, i - window)
        j_end = min(ny, i + window)

        for j in range(j_start, j_end + 1):
            cost = (x[i - 1] - y[j - 1]) ** 2

            if step_pattern == "symmetric1":
                # Only diagonal steps
                D[i, j] = cost + D[i - 1, j - 1]
            else:
                # symmetric2: diagonal, horizontal, vertical
                D[i, j] = cost + min(
                    D[i - 1, j - 1],  # diagonal
                    D[i - 1, j],       # insertion
                    D[i, j - 1],       # deletion
                )

    distance = float(np.sqrt(D[nx, ny])) if np.isfinite(D[nx, ny]) else float('inf')

    # Backtrack to find the warping path
    path = []
    i, j = nx, ny

    while i > 0 or j > 0:
        path.append((i - 1, j - 1))
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            if step_pattern == "symmetric1":
                i -= 1
                j -= 1
            else:
                choices = [
                    (D[i - 1, j - 1], i - 1, j - 1),
                    (D[i - 1, j], i - 1, j),
                    (D[i, j - 1], i, j - 1),
                ]
                _, i, j = min(choices, key=lambda c: c[0])

    path.reverse()
    return distance, D[1:, 1:], path


def _segment_lags(local_lags, threshold=2.0):
    """
    Segment the local lag series into regions of approximately constant lag.
    Uses a simple change-point approach based on deviation from running mean.
    """
    n = len(local_lags)
    if n == 0:
        return []

    segments = []
    seg_start = 0

    for i in range(1, n):
        seg_mean = np.mean(local_lags[seg_start:i])
        if abs(local_lags[i] - seg_mean) > threshold and i - seg_start > 5:
            segments.append({
                "start": seg_start,
                "end": i,
                "mean_lag": float(np.mean(local_lags[seg_start:i])),
                "std_lag": float(np.std(local_lags[seg_start:i])),
            })
            seg_start = i

    # Final segment
    segments.append({
        "start": seg_start,
        "end": n,
        "mean_lag": float(np.mean(local_lags[seg_start:n])),
        "std_lag": float(np.std(local_lags[seg_start:n])),
    })

    return segments
