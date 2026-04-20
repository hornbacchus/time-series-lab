"""
Classical Decomposition technique for Time Series Lab.

Decomposes a time series into trend, seasonal, and residual components
using either additive (Y = T + S + R) or multiplicative (Y = T * S * R) models
via statsmodels seasonal_decompose.
"""

import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose

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


def _infer_period(ctx: RunContext) -> int:
    """Infer the seasonal period from ctx.frequency or ctx.params['period']."""
    user_period = ctx.get_param("period")
    if user_period is not None:
        return int(user_period)

    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60, "S": 60,
    }
    freq = (ctx.frequency or "").strip().upper()
    if freq in freq_map:
        return freq_map[freq]
    freq_lower = (ctx.frequency or "").strip()
    if freq_lower in freq_map:
        return freq_map[freq_lower]

    raise ValueError(
        f"Cannot infer seasonal period from frequency '{ctx.frequency}'. "
        "Please supply a 'period' parameter (e.g. 12 for monthly data)."
    )


def _prepare_series(values, name, warnings):
    """Handle NaN: interpolate interior, strip edges."""
    nan_count = int(np.isnan(values).sum())
    if nan_count == 0:
        return values.copy(), None, nan_count

    warnings.append(
        f"{nan_count} missing values in '{name}'. Linearly interpolating for decomposition; "
        "original NaN positions are preserved in the output."
    )
    nan_mask = np.isnan(values)
    filled = values.copy()
    nans = np.where(nan_mask)[0]
    valid = np.where(~nan_mask)[0]
    if len(valid) < 4:
        raise ValueError(
            "Too few non-missing values to decompose. Need at least 4 valid observations."
        )
    filled[nans] = np.interp(nans, valid, values[valid])
    return filled, nan_mask, nan_count


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run classical decomposition on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    period : int, optional
        Seasonal period. Auto-inferred from ctx.frequency if omitted.
    model : str, optional
        'additive' (default) or 'multiplicative'.
    two_sided : bool, optional
        Whether to use centered moving average (True, default) or trailing.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        n = len(values)
        warnings = []

        filled, nan_mask, nan_count = _prepare_series(values, name, warnings)

        progress_callback("Inferring period", 10)
        period = _infer_period(ctx)

        if n < 2 * period:
            return make_error_response(
                ctx,
                f"Series length ({n}) must be at least 2 x period ({period}) = {2 * period}.",
                error_fixes=[
                    "Select a longer series.",
                    f"Or set 'period' to a smaller value (currently {period}).",
                ],
            )

        model_type = ctx.get_param("model", "additive").lower()
        if model_type not in ("additive", "multiplicative"):
            warnings.append(
                f"Unknown model '{model_type}'. Falling back to 'additive'."
            )
            model_type = "additive"

        # For multiplicative, all values must be positive
        if model_type == "multiplicative":
            if np.any(filled <= 0):
                warnings.append(
                    "Multiplicative decomposition requires all-positive values. "
                    "Switching to additive."
                )
                model_type = "additive"

        two_sided = ctx.get_param("two_sided", True)

        progress_callback("Running classical decomposition", 30)

        result = seasonal_decompose(
            filled,
            model=model_type,
            period=period,
            two_sided=two_sided,
            extrapolate_trend="freq",
        )

        progress_callback("Building output", 70)

        trend = result.trend.copy()
        seasonal_comp = result.seasonal.copy()
        resid = result.resid.copy()

        # Seasonally adjusted
        if model_type == "additive":
            seas_adj = filled - seasonal_comp
        else:
            seas_adj = filled / np.where(seasonal_comp == 0, np.nan, seasonal_comp)

        # Restore NaN
        if nan_mask is not None:
            trend[nan_mask] = np.nan
            seasonal_comp[nan_mask] = np.nan
            resid[nan_mask] = np.nan
            seas_adj[nan_mask] = np.nan

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
            ["Time", name, "Trend", "Seasonal", "Residual", "Seasonally Adjusted"],
            rows,
        )

        # Diagnostics
        valid_mask = ~np.isnan(resid)
        r_valid = resid[valid_mask]
        s_valid = seasonal_comp[valid_mask]
        t_valid = trend[valid_mask]

        var_r = np.var(r_valid, ddof=1) if len(r_valid) > 1 else 0.0
        if model_type == "additive":
            var_sr = np.var(s_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0
            var_tr = np.var(t_valid + r_valid, ddof=1) if len(r_valid) > 1 else 1.0
        else:
            var_sr = np.var(s_valid * r_valid, ddof=1) if len(r_valid) > 1 else 1.0
            var_tr = np.var(t_valid * r_valid, ddof=1) if len(r_valid) > 1 else 1.0

        seasonal_strength = max(0.0, 1.0 - var_r / var_sr) if var_sr > 0 else 0.0
        trend_strength = max(0.0, 1.0 - var_r / var_tr) if var_tr > 0 else 0.0

        diag_table = make_table(
            "Diagnostics",
            ["Metric", "Value"],
            [
                ["Model Type", model_type.title()],
                ["Seasonal Period", period],
                ["Two-Sided MA", two_sided],
                ["Seasonal Strength (F_s)", round(seasonal_strength, 4)],
                ["Trend Strength (F_t)", round(trend_strength, 4)],
                ["Observations", n],
                ["Missing Values", nan_count],
            ],
        )

        # Plain English
        s_pct = round(seasonal_strength * 100, 1)
        t_pct = round(trend_strength * 100, 1)
        parts = [
            f"Classical {model_type} decomposition of '{name}' "
            f"({n} observations, period={period})."
        ]
        if seasonal_strength > 0.6:
            parts.append(f"Strong seasonality detected (strength {s_pct}%).")
        elif seasonal_strength > 0.3:
            parts.append(f"Moderate seasonality (strength {s_pct}%).")
        else:
            parts.append(f"Weak seasonality (strength {s_pct}%).")

        if trend_strength > 0.6:
            parts.append(f"Strong trend component (strength {t_pct}%).")
        elif trend_strength > 0.3:
            parts.append(f"Moderate trend component (strength {t_pct}%).")
        else:
            parts.append(f"Weak trend (strength {t_pct}%).")

        charting = (
            "Line chart with 4 panels stacked vertically sharing the x-axis: "
            "Original, Trend, Seasonal, Residual. "
            "Optionally overlay Seasonally Adjusted on the Original panel as a dashed line."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("classical_decompose", {
            "series_name": name,
            "n_obs": int(len(values)),
            "period": int(period),
            "model_type": model_type,
            "two_sided": bool(two_sided),
            "seasonal_strength": float(seasonal_strength),
            "trend_strength": float(trend_strength),
        })
        return make_response(
            ctx,
            tables=[decomp_table, diag_table],
            plain_english_summary=" ".join(parts),
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "model_type": model_type,
                "period": period,
                "two_sided": two_sided,
                "seasonal_strength": round(seasonal_strength, 4),
                "trend_strength": round(trend_strength, 4),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Classical decomposition failed: {e}",
            error_fixes=[
                "Ensure your data is numeric.",
                "For multiplicative decomposition, all values must be positive.",
                "Check that the seasonal period is appropriate for your data.",
            ],
        )
