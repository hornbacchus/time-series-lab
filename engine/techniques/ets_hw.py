"""
ETS / Holt-Winters Exponential Smoothing for Time Series Lab.

Fits an Exponential Smoothing model (Simple, Holt, or Holt-Winters) using
statsmodels ExponentialSmoothing and produces forecasts with prediction intervals.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _infer_period(ctx: RunContext) -> int:
    """Infer seasonal period, return 0/1 if no seasonality."""
    user_period = ctx.get_param("seasonal_periods")
    if user_period is not None:
        return int(user_period)
    user_period = ctx.get_param("period")
    if user_period is not None:
        return int(user_period)

    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    freq = (ctx.frequency or "").strip().upper()
    if freq in freq_map:
        return freq_map[freq]
    freq_lower = (ctx.frequency or "").strip()
    if freq_lower in freq_map:
        return freq_map[freq_lower]
    return 0


def _prepare_series(values):
    """Strip edge NaN, interpolate interior. Returns (clean, n_interpolated)."""
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
    Fit ETS / Holt-Winters and generate forecasts.

    Parameters (via ctx.params)
    ---------------------------
    trend : str or None
        'add', 'mul', or None. Default: 'add'.
    seasonal : str or None
        'add', 'mul', or None. Default: auto-detect.
    seasonal_periods : int, optional
        Seasonal period. Auto-inferred if omitted.
    damped_trend : bool, optional
        Whether to use damped trend. Default False.
    horizon : int, optional
        Forecast steps. Default 10.
    use_boxcox : bool or float, optional
        Apply Box-Cox transform. Default False.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 6:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. Need at least 6.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        # Trend
        trend_param = ctx.get_param("trend", "add")
        if trend_param and str(trend_param).lower() in ("none", "null", "false"):
            trend_param = None
        elif trend_param:
            trend_param = str(trend_param).lower()[:3]
            if trend_param not in ("add", "mul"):
                trend_param = "add"

        damped = ctx.get_param("damped_trend", False)

        # Seasonal
        period = _infer_period(ctx)
        seasonal_param = ctx.get_param("seasonal")
        if seasonal_param and str(seasonal_param).lower() in ("none", "null", "false"):
            seasonal_param = None
        elif seasonal_param:
            seasonal_param = str(seasonal_param).lower()[:3]
            if seasonal_param not in ("add", "mul"):
                seasonal_param = "add"
        else:
            # Auto-detect: use seasonal if we have enough data
            if period >= 2 and n >= 2 * period:
                seasonal_param = "add"
            else:
                seasonal_param = None

        if seasonal_param is not None and (period < 2 or n < 2 * period):
            warn_list.append(
                f"Seasonal component disabled: period={period}, n={n} "
                f"(need n >= {2 * period})."
            )
            seasonal_param = None

        # Multiplicative requires all-positive values
        if seasonal_param == "mul" and np.any(clean <= 0):
            warn_list.append(
                "Multiplicative seasonal requires positive values. Switching to additive."
            )
            seasonal_param = "add"
        if trend_param == "mul" and np.any(clean <= 0):
            warn_list.append(
                "Multiplicative trend requires positive values. Switching to additive."
            )
            trend_param = "add"

        use_boxcox = ctx.get_param("use_boxcox", False)
        if use_boxcox and np.any(clean <= 0):
            warn_list.append("Box-Cox requires positive values. Disabling.")
            use_boxcox = False

        progress_callback("Fitting ETS model", 20)

        # Preset: optimize vs fixed
        optimized = True  # always optimize

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                model = ExponentialSmoothing(
                    clean,
                    trend=trend_param,
                    seasonal=seasonal_param,
                    seasonal_periods=period if seasonal_param else None,
                    damped_trend=damped if trend_param else False,
                    use_boxcox=use_boxcox,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=optimized)
            except Exception as e1:
                # Fallback: simpler model
                warn_list.append(
                    f"Full model failed ({e1}). Falling back to simpler specification."
                )
                model = ExponentialSmoothing(
                    clean,
                    trend="add",
                    seasonal=None,
                    damped_trend=False,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=True)
                trend_param = "add"
                seasonal_param = None
                damped = False

        progress_callback("Generating forecasts", 55)

        # Forecast
        fc = fit.forecast(horizon)

        # Simulation-based prediction intervals (if preset allows)
        n_sim = {"Fast": 100, "Balanced": 500, "Thorough": 1000}.get(ctx.preset, 500)
        try:
            sim = fit.simulate(horizon, repetitions=n_sim, error="mul" if seasonal_param == "mul" else "add")
            lower = np.percentile(sim, 2.5, axis=1)
            upper = np.percentile(sim, 97.5, axis=1)
        except Exception:
            # Fallback: rough interval from residual std
            resid_std = np.std(clean - fit.fittedvalues)
            lower = fc - 1.96 * resid_std
            upper = fc + 1.96 * resid_std
            warn_list.append("Prediction intervals estimated from residual std (simulation failed).")

        # In-sample
        fitted_vals = fit.fittedvalues
        residuals = clean - fitted_vals

        progress_callback("Building output", 80)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc.iloc[i] if hasattr(fc, 'iloc') else fc[i]), 6),
                round(float(lower[i]), 6),
                round(float(upper[i]), 6),
            ])
        forecast_table = make_table(
            "Forecast", ["Step", "Forecast", "Lower 95%", "Upper 95%"], fc_rows
        )

        # Fitted values table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        fit_rows = []
        for i in range(n):
            fit_rows.append([
                time_col[i],
                clean[i],
                float(fitted_vals.iloc[i] if hasattr(fitted_vals, 'iloc') else fitted_vals[i]),
                float(residuals.iloc[i] if hasattr(residuals, 'iloc') else residuals[i]),
            ])
        fitted_table = make_table(
            "Fitted Values", ["Time", name, "Fitted", "Residual"], fit_rows
        )

        # Model summary
        aic = float(fit.aic)
        bic = float(fit.bic)
        valid_resid = np.asarray(residuals)
        valid_resid = valid_resid[~np.isnan(valid_resid)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        model_desc = _describe_model(trend_param, seasonal_param, damped, period)

        summary_rows = [
            ["Model", model_desc],
            ["Trend", trend_param or "None"],
            ["Seasonal", seasonal_param or "None"],
            ["Seasonal Periods", period if seasonal_param else "N/A"],
            ["Damped Trend", damped],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Observations", n],
            ["Forecast Horizon", horizon],
        ]

        # Smoothing parameters
        params_dict = fit.params_formatted if hasattr(fit, 'params_formatted') else {}
        if hasattr(fit, 'params'):
            p = fit.params
            for k, v in p.items():
                summary_rows.append([f"Param: {k}", round(float(v), 6) if isinstance(v, (int, float, np.floating)) else v])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Plain English
        plain = (
            f"{model_desc} fitted to '{name}' ({n} observations). "
            f"AIC={aic:.1f}"
        )
        if rmse:
            plain += f", RMSE={rmse:.4f}"
        plain += f". {horizon}-step forecast produced."
        if damped:
            plain += " Damped trend reduces long-horizon forecast divergence."

        charting = (
            "Line chart with original series, fitted values overlaid, and forecast "
            "continuation with shaded 95% prediction interval. "
            "Secondary panel: residuals."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[forecast_table, fitted_table, summary_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "model": model_desc,
                "trend": trend_param,
                "seasonal": seasonal_param,
                "seasonal_periods": period if seasonal_param else None,
                "damped_trend": damped,
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "rmse": round(rmse, 4) if rmse else None,
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"ETS/Holt-Winters failed: {e}",
            error_fixes=[
                "Ensure the data is numeric.",
                "For multiplicative models, all values must be positive.",
                "Try setting trend=None or seasonal=None for simpler models.",
                "Check that the seasonal period is correct.",
            ],
        )


def _describe_model(trend, seasonal, damped, period):
    """Build a human-readable model name."""
    parts = []
    if trend is None and seasonal is None:
        return "Simple Exponential Smoothing (SES)"
    if trend and seasonal is None:
        name = "Holt's Linear" if not damped else "Damped Holt's"
        return f"{name} ({trend}. trend)"
    if trend and seasonal:
        name = "Holt-Winters"
        if damped:
            name = "Damped " + name
        return f"{name} ({trend}. trend, {seasonal}. seasonal, period={period})"
    if seasonal and trend is None:
        return f"Seasonal Exponential Smoothing ({seasonal}. seasonal, period={period})"
    return "ETS"
