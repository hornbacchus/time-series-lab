"""
MSTL (Multiple Seasonal-Trend decomposition using LOESS) for Time Series Lab.

Handles series with multiple seasonal periods (e.g. daily data with both
weekly and yearly seasonality) using statsmodels MSTL.
"""

import numpy as np
from statsmodels.tsa.seasonal import MSTL

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_FREQ_PERIODS = {
    "H": [24, 168],          # hourly: daily + weekly
    "T": [60, 1440],         # minutely: hourly + daily
    "min": [60, 1440],
    "D": [7, 365],           # daily: weekly + yearly
    "B": [5, 252],           # business-daily: weekly + yearly
    "W": [52],               # weekly: yearly
    "M": [12],               # monthly: yearly
    "MS": [12],
    "Q": [4],                # quarterly: yearly
    "QS": [4],
}


def _infer_periods(ctx: RunContext) -> list:
    """Infer seasonal periods from frequency or params."""
    user_periods = ctx.get_param("periods")
    if user_periods is not None:
        if isinstance(user_periods, (list, tuple)):
            return sorted(int(p) for p in user_periods)
        return [int(user_periods)]

    freq = (ctx.frequency or "").strip().upper()
    if freq in _FREQ_PERIODS:
        return _FREQ_PERIODS[freq]
    freq_lower = (ctx.frequency or "").strip()
    if freq_lower in _FREQ_PERIODS:
        return _FREQ_PERIODS[freq_lower]

    raise ValueError(
        f"Cannot infer seasonal periods from frequency '{ctx.frequency}'. "
        "Please supply 'periods' as a list (e.g. [7, 365] for daily data)."
    )


def _prepare_series(values, name, warnings):
    """Interpolate NaNs for MSTL."""
    nan_count = int(np.isnan(values).sum())
    if nan_count == 0:
        return values.copy(), None, nan_count

    warnings.append(
        f"{nan_count} missing values linearly interpolated for MSTL."
    )
    nan_mask = np.isnan(values)
    filled = values.copy()
    nans = np.where(nan_mask)[0]
    valid = np.where(~nan_mask)[0]
    if len(valid) < 4:
        raise ValueError("Too few non-missing values for MSTL (need >= 4).")
    filled[nans] = np.interp(nans, valid, values[valid])
    return filled, nan_mask, nan_count


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run MSTL decomposition on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    periods : list[int], optional
        List of seasonal periods. Auto-inferred from frequency if omitted.
    stl_kwargs : dict, optional
        Extra keyword arguments forwarded to each inner STL iteration.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        n = len(values)
        warnings = []

        filled, nan_mask, nan_count = _prepare_series(values, name, warnings)

        progress_callback("Inferring periods", 10)
        periods = _infer_periods(ctx)

        # Filter out periods that are too large for the data
        usable = [p for p in periods if n >= 2 * p]
        if not usable:
            return make_error_response(
                ctx,
                f"Series length ({n}) is too short for any of the requested periods {periods}. "
                f"Need at least 2 x largest period.",
                error_fixes=[
                    "Provide a longer series.",
                    "Specify smaller periods via the 'periods' parameter.",
                ],
            )
        if len(usable) < len(periods):
            dropped = [p for p in periods if p not in usable]
            warnings.append(
                f"Periods {dropped} dropped (series too short). Using {usable}."
            )
            periods = usable

        # STL kwargs based on preset
        stl_kwargs = ctx.get_param("stl_kwargs", {})
        if not isinstance(stl_kwargs, dict):
            stl_kwargs = {}

        preset_kwargs = {
            "Fast": {"seasonal_deg": 0},
            "Balanced": {"seasonal_deg": 1},
            "Thorough": {"seasonal_deg": 1},
        }
        base_kwargs = preset_kwargs.get(ctx.preset, preset_kwargs["Balanced"])
        base_kwargs.update(stl_kwargs)

        progress_callback("Running MSTL decomposition", 25)

        mstl = MSTL(filled, periods=periods, stl_kwargs=base_kwargs)
        result = mstl.fit()

        progress_callback("Building output", 70)

        trend = result.trend.values if hasattr(result.trend, 'values') else np.asarray(result.trend)
        resid = result.resid.values if hasattr(result.resid, 'values') else np.asarray(result.resid)

        # Seasonal components (one per period)
        seasonal_df = result.seasonal
        if hasattr(seasonal_df, 'columns'):
            seasonal_names = list(seasonal_df.columns)
            seasonal_arrays = [seasonal_df.iloc[:, i].values for i in range(len(seasonal_names))]
        else:
            seasonal_names = [f"Seasonal_{p}" for p in periods]
            seasonal_arrays = [np.asarray(seasonal_df)]

        # Restore NaN
        if nan_mask is not None:
            trend[nan_mask] = np.nan
            resid[nan_mask] = np.nan
            for arr in seasonal_arrays:
                arr[nan_mask] = np.nan

        # Build decomposition table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        columns = ["Time", name, "Trend"] + seasonal_names + ["Residual"]
        rows = []
        for i in range(n):
            row = [time_col[i], values[i], trend[i]]
            for arr in seasonal_arrays:
                row.append(arr[i])
            row.append(resid[i])
            rows.append(row)

        decomp_table = make_table("MSTL Decomposition", columns, rows)

        # Strength metrics for each seasonal component
        valid_mask = ~np.isnan(resid)
        r_valid = resid[valid_mask]
        var_r = np.var(r_valid, ddof=1) if len(r_valid) > 1 else 0.0

        strengths = []
        for sname, sarr in zip(seasonal_names, seasonal_arrays):
            s_valid = sarr[valid_mask]
            var_sr = np.var(s_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0
            fs = max(0.0, 1.0 - var_r / var_sr) if var_sr > 0 else 0.0
            strengths.append((sname, round(fs, 4)))

        t_valid = trend[valid_mask]
        var_tr = np.var(t_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0
        trend_strength = max(0.0, 1.0 - var_r / var_tr) if var_tr > 0 else 0.0

        diag_rows = [
            ["Periods", str(periods)],
            ["Trend Strength (F_t)", round(trend_strength, 4)],
        ]
        for sname, fs in strengths:
            diag_rows.append([f"Strength: {sname}", fs])
        diag_rows.append(["Observations", n])
        diag_rows.append(["Missing Values Interpolated", nan_count])
        diag_rows.append(["Preset", ctx.preset])

        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        # Plain English
        parts = [
            f"MSTL decomposition of '{name}' ({n} observations) with "
            f"{len(periods)} seasonal period(s): {periods}."
        ]
        for sname, fs in strengths:
            pct = round(fs * 100, 1)
            label = "strong" if fs > 0.6 else ("moderate" if fs > 0.3 else "weak")
            parts.append(f"{sname}: {label} ({pct}%).")

        t_pct = round(trend_strength * 100, 1)
        label = "strong" if trend_strength > 0.6 else ("moderate" if trend_strength > 0.3 else "weak")
        parts.append(f"Trend: {label} ({t_pct}%).")

        charting = (
            f"Line chart with {2 + len(periods)} panels stacked vertically sharing the x-axis: "
            "Original, Trend, " + ", ".join(seasonal_names) + ", Residual."
        )

        progress_callback("Done", 100)

        audit = {
            "periods": periods,
            "trend_strength": round(trend_strength, 4),
        }
        for sname, fs in strengths:
            audit[f"strength_{sname}"] = fs

        return make_response(
            ctx,
            tables=[decomp_table, diag_table],
            plain_english_summary=" ".join(parts),
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"MSTL decomposition failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with no text values.",
                "Check that the periods are appropriate for your data frequency.",
                "If the series is very short, use fewer or smaller periods.",
            ],
        )
