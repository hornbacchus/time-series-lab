"""
PELT Change Point Detection for Time Series Lab.

Detects abrupt changes in the statistical properties of a time series
(mean, variance, or both) using the PELT algorithm from the ``ruptures`` package.
"""

import numpy as np
import ruptures as rpt

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
    Detect change points using the PELT algorithm.

    Parameters (via ctx.params)
    ---------------------------
    model : str, optional
        Cost model: 'l2' (mean shift, default), 'l1', 'rbf' (non-parametric),
        'normal' (mean+variance), 'ar' (autoregressive).
    min_size : int, optional
        Minimum segment length. Default 5.
    penalty : float or str, optional
        Penalty value or method. Float = manual BIC-like penalty.
        'bic' / 'aic' / 'mbic' = automatic. Default depends on preset.
    n_bkps : int, optional
        If provided, use Binseg with fixed number of breakpoints instead of PELT.
    jump : int, optional
        Grid step for search (larger = faster, less precise). Default 1.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 15:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. Need at least 15.",
                error_fixes=["Provide a longer time series."],
            )

        cost_model = ctx.get_param("model", "l2")
        min_size = int(ctx.get_param("min_size", 5))
        jump = int(ctx.get_param("jump", 1))
        n_bkps = ctx.get_param("n_bkps")

        # Penalty
        penalty_param = ctx.get_param("penalty")
        if penalty_param is None:
            # Preset-based default
            preset_pen = {
                "Fast": "bic",
                "Balanced": "bic",
                "Thorough": "mbic",
            }
            penalty_method = preset_pen.get(ctx.preset, "bic")
        elif isinstance(penalty_param, (int, float)):
            penalty_method = float(penalty_param)
        else:
            penalty_method = str(penalty_param).lower()

        progress_callback("Running change point detection", 20)

        signal = clean.reshape(-1, 1)

        if n_bkps is not None:
            # Fixed number of breakpoints: use Binseg or BottomUp
            n_bkps = int(n_bkps)
            algo = rpt.Binseg(model=cost_model, min_size=min_size, jump=jump).fit(signal)
            bkps = algo.predict(n_bkps=n_bkps)
        else:
            # PELT with penalty
            algo = rpt.Pelt(model=cost_model, min_size=min_size, jump=jump).fit(signal)
            if isinstance(penalty_method, float):
                bkps = algo.predict(pen=penalty_method)
            else:
                # Use BIC-like penalty: pen = log(n) * dim * sigma^2
                # For automatic penalty, use a heuristic
                sigma2 = np.var(clean)
                if penalty_method == "aic":
                    pen = 2 * sigma2
                elif penalty_method == "mbic":
                    pen = 3 * np.log(n) * sigma2
                else:  # bic
                    pen = np.log(n) * sigma2

                bkps = algo.predict(pen=pen)

        # bkps includes n as the last element (end of final segment)
        # Remove trailing n if present
        if bkps and bkps[-1] == n:
            change_points = bkps[:-1]
        else:
            change_points = bkps

        n_cp = len(change_points)

        progress_callback("Analyzing segments", 60)

        # Build segment statistics
        boundaries = [0] + change_points + [n]
        seg_rows = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            segment = clean[start:end]
            seg_mean = float(np.mean(segment))
            seg_std = float(np.std(segment, ddof=1)) if len(segment) > 1 else 0.0
            seg_min = float(np.min(segment))
            seg_max = float(np.max(segment))
            seg_rows.append([
                i + 1,
                start + 1,  # 1-indexed
                end,
                end - start,
                round(seg_mean, 4),
                round(seg_std, 4),
                round(seg_min, 4),
                round(seg_max, 4),
            ])

        seg_table = make_table(
            "Segments",
            ["Segment", "Start", "End", "Length", "Mean", "Std Dev", "Min", "Max"],
            seg_rows,
        )

        # Change points table
        cp_rows = []
        for i, cp in enumerate(change_points):
            # Mean shift at this point
            before_start = boundaries[i]
            before = clean[before_start:cp]
            after_end = boundaries[i + 2] if i + 2 < len(boundaries) else n
            after = clean[cp:after_end]
            mean_before = float(np.mean(before)) if len(before) > 0 else None
            mean_after = float(np.mean(after)) if len(after) > 0 else None
            shift = round(mean_after - mean_before, 4) if mean_before is not None and mean_after is not None else None

            # Map to time if available
            time_label = ctx.time[cp] if ctx.time and cp < len(ctx.time) else cp + 1

            cp_rows.append([
                i + 1,
                cp + 1,  # 1-indexed position
                time_label,
                round(mean_before, 4) if mean_before is not None else None,
                round(mean_after, 4) if mean_after is not None else None,
                shift,
            ])

        cp_table = make_table(
            "Change Points",
            ["#", "Position", "Time", "Mean Before", "Mean After", "Shift"],
            cp_rows,
        )

        # Full series with segment labels
        label_rows = []
        seg_labels = np.zeros(n, dtype=int)
        for i in range(len(boundaries) - 1):
            seg_labels[boundaries[i]:boundaries[i + 1]] = i + 1

        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        step = max(1, n // 500)  # subsample for large series
        for i in range(0, n, step):
            label_rows.append([time_col[i], clean[i], seg_labels[i]])
        label_table = make_table(
            "Series with Segment Labels",
            ["Time", name, "Segment"],
            label_rows,
        )

        # Diagnostics
        diag_rows = [
            ["Cost Model", cost_model],
            ["Penalty", str(penalty_method)],
            ["Min Segment Size", min_size],
            ["Change Points Detected", n_cp],
            ["Number of Segments", n_cp + 1],
            ["Observations", n],
            ["Preset", ctx.preset],
        ]
        diag_table = make_table("Detection Parameters", ["Metric", "Value"], diag_rows)

        # Plain English
        if n_cp == 0:
            plain = (
                f"No change points detected in '{name}' ({n} observations) "
                f"using the {cost_model.upper()} cost model. "
                "The series appears homogeneous with no abrupt shifts in its statistical properties."
            )
        elif n_cp == 1:
            cp_pos = change_points[0]
            plain = (
                f"1 change point detected in '{name}' at position {cp_pos + 1} "
                f"(out of {n} observations). "
            )
            if cp_rows[0][5] is not None:
                plain += f"Mean shifted by {cp_rows[0][5]:+.4f}. "
            plain += "The series is split into 2 distinct segments."
        else:
            plain = (
                f"{n_cp} change points detected in '{name}' ({n} observations), "
                f"dividing the series into {n_cp + 1} segments. "
            )
            # Describe the largest shift
            shifts = [(abs(r[5]) if r[5] is not None else 0, r[1], r[5]) for r in cp_rows]
            shifts.sort(reverse=True)
            if shifts and shifts[0][2] is not None:
                plain += (
                    f"Largest shift at position {shifts[0][1]}: {shifts[0][2]:+.4f}."
                )

        charting = (
            "Line chart of the series with vertical dashed lines at each change point. "
            "Color or shade each segment differently. "
            "Optionally show segment means as horizontal lines within each segment."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[cp_table, seg_table, diag_table, label_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "cost_model": cost_model,
                "penalty": str(penalty_method),
                "min_size": min_size,
                "n_change_points": n_cp,
                "change_point_positions": [cp + 1 for cp in change_points],
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"PELT change point detection failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try a different cost model ('l2', 'rbf', 'normal').",
                "Adjust the penalty to control sensitivity (higher = fewer change points).",
                "For very short series, increase min_size or use n_bkps for a fixed count.",
            ],
        )
