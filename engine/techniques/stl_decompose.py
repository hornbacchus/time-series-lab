"""
STL Decomposition technique for Time Series Lab.

Decomposes a time series into trend, seasonal, and remainder components
using Seasonal-Trend decomposition using LOESS (STL).
"""

import numpy as np
from statsmodels.tsa.seasonal import STL

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


# Preset -> seasonal_deg and number of inner/outer iterations
_PRESET_CONFIG = {
    "Fast": {"seasonal_deg": 0, "inner_iter": 2, "outer_iter": 0},
    "Balanced": {"seasonal_deg": 1, "inner_iter": 5, "outer_iter": 2},
    "Thorough": {"seasonal_deg": 1, "inner_iter": 10, "outer_iter": 5},
}


def _infer_period(ctx: RunContext) -> int:
    """
    Infer the seasonal period from the frequency string.
    Falls back to a user-supplied 'period' parameter or raises.
    """
    user_period = ctx.get_param("period")
    if user_period is not None:
        return int(user_period)

    freq_map = {
        "D": 7,
        "B": 5,
        "W": 52,
        "M": 12,
        "MS": 12,
        "Q": 4,
        "QS": 4,
        "H": 24,
        "T": 60,
        "min": 60,
        "S": 60,
    }
    freq = (ctx.frequency or "").strip().upper()
    # Try exact match first
    if freq in freq_map:
        return freq_map[freq]
    # Try lowercase original
    freq_lower = (ctx.frequency or "").strip()
    if freq_lower in freq_map:
        return freq_map[freq_lower]

    raise ValueError(
        f"Cannot infer seasonal period from frequency '{ctx.frequency}'. "
        "Please supply a 'period' parameter (e.g. 12 for monthly data with yearly seasonality)."
    )


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run STL decomposition on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    period : int, optional
        Seasonal period. Auto-inferred from ctx.frequency if omitted.
    seasonal : int, optional
        Length of the seasonal smoother (must be odd, >= 7).
        Defaults depend on preset.
    robust : bool, optional
        Whether to use robust fitting (downweights outliers). Default True.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        n = len(values)
        warnings = []

        # Handle NaN: STL requires no interior NaNs.
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0:
            warnings.append(
                f"{nan_count} missing values detected. Linearly interpolating for STL; "
                "original NaN positions are preserved in the output."
            )
            # Interpolate for STL, keep mask for output
            nan_mask = np.isnan(values)
            filled = values.copy()
            nans = np.where(nan_mask)[0]
            valid = np.where(~nan_mask)[0]
            if len(valid) < 4:
                return make_error_response(
                    ctx,
                    "Too few non-missing values to decompose. Need at least 4 valid observations.",
                    error_fixes=["Check your data for excessive missing values."],
                )
            filled[nans] = np.interp(nans, valid, values[valid])
        else:
            filled = values
            nan_mask = None

        progress_callback("Inferring period", 10)
        period = _infer_period(ctx)

        if n < 2 * period:
            return make_error_response(
                ctx,
                f"Series length ({n}) must be at least 2 x period ({period}) = {2 * period}. "
                f"You have too few observations for seasonal period {period}.",
                error_fixes=[
                    "Select a longer series.",
                    f"Or set 'period' to a smaller value (currently {period}).",
                ],
            )

        # Determine seasonal window
        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        seasonal = ctx.get_param("seasonal")
        if seasonal is None:
            # Default: period + 1 if odd, period + 2 if even (ensures odd, >= 7)
            seasonal = period + (1 if period % 2 == 0 else 2)
            seasonal = max(seasonal, 7)
        else:
            seasonal = int(seasonal)
            if seasonal % 2 == 0:
                seasonal += 1
                warnings.append(f"'seasonal' must be odd; adjusted to {seasonal}.")

        robust = ctx.get_param("robust", True)

        progress_callback("Running STL decomposition", 30)

        stl = STL(
            filled,
            period=period,
            seasonal=seasonal,
            seasonal_deg=preset_cfg["seasonal_deg"],
            robust=robust,
        )
        result = stl.fit(inner_iter=preset_cfg["inner_iter"], outer_iter=preset_cfg["outer_iter"])

        progress_callback("Building output", 75)

        trend = result.trend
        seasonal_comp = result.seasonal
        resid = result.resid
        seas_adj = filled - seasonal_comp

        # Restore NaN positions in output
        if nan_mask is not None:
            trend[nan_mask] = np.nan
            seasonal_comp[nan_mask] = np.nan
            resid[nan_mask] = np.nan
            seas_adj[nan_mask] = np.nan

        # Build decomposition table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        rows = []
        for i in range(n):
            rows.append([
                time_col[i],
                values[i],
                trend[i],
                seasonal_comp[i],
                resid[i],
                seas_adj[i],
            ])

        decomp_table = make_table(
            "Decomposition",
            ["Time", name, "Trend", "Seasonal", "Remainder", "Seasonally Adjusted"],
            rows,
        )

        # Diagnostics: seasonal strength and trend strength
        # Using standard formulas: F_s = max(0, 1 - Var(R) / Var(S + R))
        valid_mask = ~np.isnan(resid) if nan_mask is not None else np.ones(n, dtype=bool)
        r_valid = resid[valid_mask]
        s_valid = seasonal_comp[valid_mask]
        t_valid = trend[valid_mask]

        var_r = np.var(r_valid, ddof=1) if len(r_valid) > 1 else 0.0
        var_sr = np.var(s_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0
        var_tr = np.var(t_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0

        seasonal_strength = max(0.0, 1.0 - var_r / var_sr) if var_sr > 0 else 0.0
        trend_strength = max(0.0, 1.0 - var_r / var_tr) if var_tr > 0 else 0.0

        diag_table = make_table(
            "Diagnostics",
            ["Metric", "Value"],
            [
                ["Seasonal Period", period],
                ["Seasonal Window", seasonal],
                ["Seasonal Strength (F_s)", round(seasonal_strength, 4)],
                ["Trend Strength (F_t)", round(trend_strength, 4)],
                ["Observations", n],
                ["Missing Values", nan_count],
                ["Robust Fitting", robust],
                ["Preset", ctx.preset],
            ],
        )

        # Plain English summary
        s_pct = round(seasonal_strength * 100, 1)
        t_pct = round(trend_strength * 100, 1)
        summary_parts = [f"STL decomposition of '{name}' ({n} observations, period={period})."]
        if seasonal_strength > 0.6:
            summary_parts.append(f"Strong seasonality detected (strength {s_pct}%).")
        elif seasonal_strength > 0.3:
            summary_parts.append(f"Moderate seasonality detected (strength {s_pct}%).")
        else:
            summary_parts.append(f"Weak seasonality (strength {s_pct}%).")

        if trend_strength > 0.6:
            summary_parts.append(f"Strong trend component (strength {t_pct}%).")
        elif trend_strength > 0.3:
            summary_parts.append(f"Moderate trend component (strength {t_pct}%).")
        else:
            summary_parts.append(f"Weak trend (strength {t_pct}%).")

        plain_english = " ".join(summary_parts)

        progress_callback("Done", 100)

        charting = (
            "Line chart with 4 panels stacked vertically sharing the x-axis: "
            "Original, Trend, Seasonal, Remainder. "
            "Optionally overlay Seasonally Adjusted on the Original panel as a dashed line."
        )

        interp = build_interpretation("stl_decompose", {
            "series_name": name,
            "n_obs": int(len(values)),
            "period": int(period),
            "seasonal_window": seasonal,
            "seasonal_strength": float(seasonal_strength),
            "trend_strength": float(trend_strength),
            "robust": bool(robust),
        })
        return make_response(
            ctx,
            tables=[decomp_table, diag_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "period": period,
                "seasonal_window": seasonal,
                "seasonal_strength": round(seasonal_strength, 4),
                "trend_strength": round(trend_strength, 4),
                "robust": robust,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"STL decomposition failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with no text values.",
                "Check that the seasonal period is appropriate for your data frequency.",
                "If the series is very short, try a smaller period.",
            ],
        )
