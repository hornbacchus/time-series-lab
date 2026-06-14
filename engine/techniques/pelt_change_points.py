"""
PELT Change Point Detection for Time Series Lab.

Detects abrupt changes in the statistical properties of a time series
(mean, variance, or both) using the PELT algorithm via ``ruptures``.
PELT (Pruned Exact Linear Time) is exact for the additive cost +
penalty objective; runs in O(T log T) with the linear-time pruning
trick.

References
----------
Killick, Fearnhead & Eckley 2012 (PELT algorithm); Truong, Oudre &
Vayatis 2020 (ruptures package). Reference parity check: same-library
Pattern A.1 against ruptures.Pelt (Phase 3 audit p3_pelt; closed-form
match given identical cost function + penalty).

Audit fields
------------
- ``change_points``: list of T-indices where PELT detected breaks
  (returned by ``ruptures.Pelt(...).fit_predict()``; the final entry
  is always T itself per ruptures convention).
- ``cost_function``, ``penalty``: the cost class name (e.g., l2 /
  rbf / cosine) and penalty value used; reproduces the exact PELT
  invocation for downstream verification.
"""

import numpy as np
import ruptures as rpt

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


def _multivariate_penalty(penalty_method, n, X):
    """Dimensionally-correct multivariate BIC-family penalty for the
    ruptures l2 cost.

    The l2 segment cost sums squared deviations ACROSS features, so the
    penalty must scale with the summed per-feature noise variance. This
    reduces EXACTLY to the univariate ``log(n)*sigma2`` at k=1 (a single
    column), and generalizes it to ``log(n)*sum_j(var_j)`` for k columns
    — the standard multivariate-BIC scaling (each change point adds a
    k-dim mean = k parameters, normalized by the per-feature noise).
    """
    sum_var = float(np.sum(np.var(X, axis=0)))
    if penalty_method == "aic":
        return 2 * sum_var
    if penalty_method == "mbic":
        return 3 * np.log(n) * sum_var
    return np.log(n) * sum_var  # bic


def _run_multivariate(ctx, progress_callback, all_series):
    """Multivariate (joint-across-curve-points) PELT — ENG-EXT-CHANGEPOINT-001
    A1a. Detects a SINGLE JOINT change-point set common across all input
    series (the curve-wide regime-shift dates), using ruptures' native
    multivariate cost support. Invoked when >=2 series are supplied; the
    univariate path (1 series) is unchanged.
    """
    warn_list = []
    names = [s[0] for s in all_series]
    arrays = [np.asarray(s[1], dtype=float) for s in all_series]
    k = len(names)

    # Align to common length (mirror vecm_model / hmm_model stacking).
    min_len = min(len(a) for a in arrays)
    if any(len(a) != min_len for a in arrays):
        warn_list.append(f"Series aligned to common length {min_len}.")
    # Per-column interior+edge NaN interpolation, length-preserving (so
    # all columns stay aligned for the joint (n,k) signal).
    cols = []
    total_interp = 0
    for a in arrays:
        col = a[:min_len].copy()
        nans = np.where(np.isnan(col))[0]
        valid = np.where(~np.isnan(col))[0]
        if len(nans) > 0 and len(valid) >= 2:
            col[nans] = np.interp(nans, valid, col[valid])
            total_interp += len(nans)
        cols.append(col)
    if total_interp > 0:
        warn_list.append(f"{total_interp} missing values linearly interpolated (per series).")

    X = np.column_stack(cols)  # (n, k)
    n = X.shape[0]
    if n < 15:
        return make_error_response(
            ctx,
            f"Only {n} aligned observations across {k} series. Need at least 15.",
            error_fixes=["Provide longer time series."],
        )

    cost_model = ctx.get_param("model", "l2")
    min_size = int(ctx.get_param("min_size", 5))
    jump = int(ctx.get_param("jump", 1))
    n_bkps = ctx.get_param("n_bkps")
    if isinstance(n_bkps, str) and n_bkps.strip() == "":
        n_bkps = None  # empty textbox == unset (penalty-based detection)

    # Penalty. Precedence: a numeric Penalty Value (manual override) wins over
    # the Penalty dropdown, which falls back to the preset-based "auto".
    # (n_bkps, handled below, overrides ALL of these.)
    penalty_value_param = ctx.get_param("penalty_value")
    if isinstance(penalty_value_param, str) and penalty_value_param.strip() == "":
        penalty_value_param = None  # empty textbox == unset
    if penalty_value_param is not None:
        try:
            penalty_method = float(penalty_value_param)
        except (TypeError, ValueError):
            return make_error_response(
                ctx,
                f"Penalty Value must be a number, got {penalty_value_param!r}.",
                error_fixes=["Enter a positive number, or clear Penalty Value to use the Penalty criterion."],
            )
        if penalty_method <= 0:
            return make_error_response(
                ctx,
                f"Penalty Value must be > 0 when set, got {penalty_method}.",
                error_fixes=["Use a positive penalty, or clear Penalty Value to use the Penalty criterion."],
            )
    else:
        penalty_param = ctx.get_param("penalty")
        # "auto" (the dialog default) is a SENTINEL for the preset-based automatic
        # penalty (== unset). bic/aic/mbic tokens and numerics pass through below.
        if isinstance(penalty_param, str) and penalty_param.strip().lower() in ("", "auto", "none"):
            penalty_param = None
        if penalty_param is None:
            penalty_method = {"Fast": "bic", "Balanced": "bic",
                              "Thorough": "mbic"}.get(ctx.preset, "bic")
        elif isinstance(penalty_param, (int, float)):
            penalty_method = float(penalty_param)
        else:
            penalty_method = str(penalty_param).lower()

    _PENALTY_METHOD_OPTS = ("bic", "aic", "mbic")
    if isinstance(penalty_method, str) and penalty_method not in _PENALTY_METHOD_OPTS:
        return make_error_response(
            ctx,
            f"Unknown penalty method '{penalty_method}'. Must be one of: "
            f"{', '.join(_PENALTY_METHOD_OPTS)} (or a numeric value).",
            error_fixes=["Use 'bic', 'aic', 'mbic', or a numeric penalty."],
        )

    progress_callback("Running multivariate change point detection", 20)

    # Joint multivariate PELT — pass the (n,k) signal directly (no reshape).
    if n_bkps is not None:
        n_bkps = int(n_bkps)
        # Exact feasible bound: K+1 segments each >= min_size on n points
        # => K <= floor(n/min_size) - 1.
        _max_bkps = n // min_size - 1
        if n_bkps < 0 or n_bkps > _max_bkps:
            return make_error_response(
                ctx,
                f"Number of Breakpoints ({n_bkps}) is out of range: with "
                f"{n} observations and Min Segment Size {min_size}, at most "
                f"{_max_bkps} breakpoint(s) are feasible ({n_bkps + 1} "
                f"segments each need >= {min_size} points).",
                error_fixes=[f"Use a value between 0 and {_max_bkps}, or lower Min Segment Size."],
            )
        warn_list.append(
            f"Break count forced to {n_bkps}; penalty criterion ignored "
            f"(Number of Breakpoints overrides penalty)."
        )
        algo = rpt.Binseg(model=cost_model, min_size=min_size, jump=jump).fit(X)
        bkps = algo.predict(n_bkps=n_bkps)
        penalty_value = None
    else:
        algo = rpt.Pelt(model=cost_model, min_size=min_size, jump=jump).fit(X)
        if isinstance(penalty_method, float):
            penalty_value = float(penalty_method)
        else:
            penalty_value = float(_multivariate_penalty(penalty_method, n, X))
        bkps = algo.predict(pen=penalty_value)

    change_points = bkps[:-1] if (bkps and bkps[-1] == n) else bkps
    n_cp = len(change_points)

    progress_callback("Analyzing segments", 60)
    boundaries = [0] + list(change_points) + [n]

    # Joint Change Points table (curve-wide regime dates).
    cp_rows = []
    for i, cp in enumerate(change_points):
        time_label = ctx.time[cp] if ctx.time and cp < len(ctx.time) else cp + 1
        cp_rows.append([i + 1, cp + 1, time_label])
    cp_table = make_table(
        "Change Points (joint, curve-wide)",
        ["#", "Position", "Time"], cp_rows,
    )

    # Multivariate Segments table: per-segment per-series mean (wide).
    seg_rows = []
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        row = [i + 1, start + 1, end, end - start]
        for j in range(k):
            row.append(round(float(np.mean(X[start:end, j])), 4))
        seg_rows.append(row)
    seg_table = make_table(
        "Segments (per-series means)",
        ["Segment", "Start", "End", "Length"] + [f"Mean({names[j]})" for j in range(k)],
        seg_rows,
    )

    diag_table = make_table(
        "Detection Parameters",
        ["Metric", "Value"],
        [
            ["Mode", "multivariate (joint)"],
            ["Series (features)", ", ".join(names)],
            ["n_features", k],
            ["Cost Model", cost_model],
            ["Penalty", str(penalty_method)],
            ["Penalty Value", round(penalty_value, 6) if penalty_value is not None else "n_bkps"],
            ["Min Segment Size", min_size],
            ["Change Points Detected", n_cp],
            ["Number of Segments", n_cp + 1],
            ["Observations", n],
            ["Preset", ctx.preset],
        ],
    )

    if n_cp == 0:
        plain = (
            f"No joint change points detected across {k} series "
            f"({', '.join(names)}; {n} aligned observations) using the "
            f"{cost_model.upper()} cost model — the curve appears regime-stable."
        )
    else:
        positions = ", ".join(str(cp + 1) for cp in change_points)
        plain = (
            f"{n_cp} joint (curve-wide) change point(s) detected across {k} "
            f"series ({', '.join(names)}; {n} observations) at position(s) "
            f"{positions}, dividing the curve into {n_cp + 1} joint regimes. "
            "Each change point is a date where the WHOLE curve shifts regime "
            "simultaneously (joint multivariate detection)."
        )

    charting = (
        "Multi-panel: each series stacked, with shared vertical dashed lines at "
        "the joint change points (curve-wide regime dates). Shade joint segments."
    )

    progress_callback("Done", 100)
    return make_response(
        ctx,
        tables=[cp_table, seg_table, diag_table],
        plain_english_summary=plain,
        warnings=warn_list,
        charting_suggestions=charting,
        interpretation=None,
        audit_fields={
            "mode": "multivariate",
            "n_features": k,
            "features": names,
            "cost_model": cost_model,
            "penalty": str(penalty_method),
            "penalty_value": round(penalty_value, 6) if penalty_value is not None else None,
            "min_size": min_size,
            "n_change_points": n_cp,
            "change_point_positions": [cp + 1 for cp in change_points],
        },
    )


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

        # Multivariate joint-detection auto-detect (ENG-EXT-CHANGEPOINT-001
        # A1a): >=2 input series -> joint multivariate PELT across the curve
        # (the curve-wide regime-shift dates). Exactly 1 series -> the
        # univariate path below, UNCHANGED / backward-compatible.
        _all_series = ctx.get_all_series()
        if len(_all_series) >= 2:
            return _run_multivariate(ctx, progress_callback, _all_series)

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
        if isinstance(n_bkps, str) and n_bkps.strip() == "":
            n_bkps = None  # empty textbox == unset (penalty-based detection)

        # Penalty. Precedence: a numeric Penalty Value (manual override) wins
        # over the Penalty dropdown, which falls back to the preset-based
        # "auto". (n_bkps, handled below, overrides ALL of these.)
        penalty_value_param = ctx.get_param("penalty_value")
        if isinstance(penalty_value_param, str) and penalty_value_param.strip() == "":
            penalty_value_param = None  # empty textbox == unset
        if penalty_value_param is not None:
            try:
                penalty_method = float(penalty_value_param)
            except (TypeError, ValueError):
                return make_error_response(
                    ctx,
                    f"Penalty Value must be a number, got {penalty_value_param!r}.",
                    error_fixes=["Enter a positive number, or clear Penalty Value to use the Penalty criterion."],
                )
            if penalty_method <= 0:
                return make_error_response(
                    ctx,
                    f"Penalty Value must be > 0 when set, got {penalty_method}.",
                    error_fixes=["Use a positive penalty, or clear Penalty Value to use the Penalty criterion."],
                )
        else:
            # Penalty
            penalty_param = ctx.get_param("penalty")
            # "auto" (the dialog default) is a SENTINEL for the preset-based
            # automatic penalty (== unset). bic/aic/mbic tokens and numerics pass
            # through below.
            if isinstance(penalty_param, str) and penalty_param.strip().lower() in ("", "auto", "none"):
                penalty_param = None
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

        # CAI Phase 2 Session 15 fix (F-CP-PELT-PENALTY): explicit
        # allowlist gate. Pre-fix, invalid string penalties (e.g.
        # "zzz") fell through the if/elif/else chain at the
        # algo.predict() call site to the `else: # bic` branch
        # silently. audit_fields["penalty"] still reported the
        # user's invalid string, misrepresenting the model.
        _PENALTY_METHOD_OPTS = ("bic", "aic", "mbic")
        if isinstance(penalty_method, str) and penalty_method not in _PENALTY_METHOD_OPTS:
            return make_error_response(
                ctx,
                f"Unknown penalty method '{penalty_method}'. Must "
                f"be one of: {', '.join(_PENALTY_METHOD_OPTS)} "
                f"(or supply a numeric penalty value).",
                error_fixes=[
                    "Use 'bic' (default; log(n)·sigma² penalty), "
                    "'aic' (2·sigma² penalty), or 'mbic' (modified "
                    "BIC; 3·log(n)·sigma² penalty), OR pass a "
                    "numeric value for a manual penalty.",
                ],
            )

        progress_callback("Running change point detection", 20)

        signal = clean.reshape(-1, 1)

        if n_bkps is not None:
            # Fixed number of breakpoints: use Binseg (overrides the penalty).
            n_bkps = int(n_bkps)
            # Exact feasible bound: K+1 segments each >= min_size on n points
            # => K <= floor(n/min_size) - 1.
            _max_bkps = n // min_size - 1
            if n_bkps < 0 or n_bkps > _max_bkps:
                return make_error_response(
                    ctx,
                    f"Number of Breakpoints ({n_bkps}) is out of range: with "
                    f"{n} observations and Min Segment Size {min_size}, at most "
                    f"{_max_bkps} breakpoint(s) are feasible ({n_bkps + 1} "
                    f"segments each need >= {min_size} points).",
                    error_fixes=[f"Use a value between 0 and {_max_bkps}, or lower Min Segment Size."],
                )
            warn_list.append(
                f"Break count forced to {n_bkps}; penalty criterion ignored "
                f"(Number of Breakpoints overrides penalty)."
            )
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

        # Extract most-recent change point details + largest segment.
        _most_recent_date = cp_rows[-1][2] if cp_rows else None
        _most_recent_pre = cp_rows[-1][3] if cp_rows else None
        _most_recent_post = cp_rows[-1][4] if cp_rows else None
        _largest_segment = max(
            (boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)),
            default=n,
        )
        _penalty_numeric = (
            float(penalty_method) if isinstance(penalty_method, (int, float)) else None
        )
        interp = build_interpretation("pelt_change_points", {
            "series_name": name,
            "n_obs": int(n),
            "n_change_points": int(n_cp),
            "cost_model": str(cost_model).upper(),
            "penalty": _penalty_numeric,
            "most_recent_cp_date": _most_recent_date,
            "most_recent_pre_mean": _most_recent_pre,
            "most_recent_post_mean": _most_recent_post,
            "largest_segment_size": int(_largest_segment),
        })
        return make_response(
            ctx,
            tables=[cp_table, seg_table, diag_table, label_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
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
