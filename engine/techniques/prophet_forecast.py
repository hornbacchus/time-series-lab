"""
Facebook Prophet Forecast for Time Series Lab.

Uses the Prophet library for additive/multiplicative decomposition-based
forecasting. Falls back to a seasonal naive method if Prophet is not installed.
Prophet excels at data with strong seasonality and multiple change points.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _has_prophet():
    try:
        from prophet import Prophet
        return True
    except ImportError:
        return False


_PRESET_CONFIG = {
    "Fast": {
        "changepoint_prior_scale": 0.1,
        "seasonality_prior_scale": 10.0,
        "n_changepoints": 15,
        "mcmc_samples": 0,
    },
    "Balanced": {
        "changepoint_prior_scale": 0.05,
        "seasonality_prior_scale": 10.0,
        "n_changepoints": 25,
        "mcmc_samples": 0,
    },
    "Thorough": {
        "changepoint_prior_scale": 0.01,
        "seasonality_prior_scale": 10.0,
        "n_changepoints": 50,
        "mcmc_samples": 0,
    },
}


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([]), 0
    trimmed = values[first_valid:last_valid + 1].copy()
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


def _seasonal_naive_forecast(series, horizon, period):
    """
    Seasonal naive fallback: repeat the last full seasonal cycle.
    Also provides simple confidence intervals based on historical residuals.
    """
    n = len(series)
    if period is None or period < 2:
        period = 1

    # Build forecasts by repeating the last seasonal cycle
    forecasts = []
    for h in range(horizon):
        idx = n - period + (h % period)
        if idx < 0:
            idx = n - 1
        forecasts.append(series[idx])

    forecasts = np.array(forecasts)

    # Compute naive residuals for intervals and derive a t-critical
    # half-width. The old code used 1.96 (z for 97.5%) which assumes
    # known variance and infinite DoF — too narrow on small samples.
    # Scale by √h to let the interval widen with the forecast horizon
    # (consistent with a random-walk error for the seasonal-naive
    # baseline that this fallback approximates).
    residuals = []
    for i in range(period, n):
        residuals.append(series[i] - series[i - period])
    if len(residuals) > 0:
        std_resid = float(np.std(residuals, ddof=1))
        dof = max(1, len(residuals) - 1)
    else:
        std_resid = float(np.std(series, ddof=1))
        dof = max(1, n - 1)

    from scipy.stats import t as _t_dist
    t_crit = float(_t_dist.ppf(0.975, dof))
    horizon_scale = np.sqrt(np.arange(1, horizon + 1))
    half_width = t_crit * std_resid * horizon_scale
    lower = forecasts - half_width
    upper = forecasts + half_width

    return forecasts, lower, upper, std_resid


def _infer_period(frequency):
    """Infer seasonal period from frequency string."""
    if not frequency:
        return None
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60, "S": 60,
    }
    freq = frequency.strip().upper()
    return freq_map.get(freq, None)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Facebook Prophet forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    yearly_seasonality : str
        'auto' (default), 'true', or 'false'.
    weekly_seasonality : str
        'auto' (default), 'true', or 'false'.
    changepoint_prior_scale : float
        Flexibility of trend changepoints. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")
        n = len(clean)

        if n < 10:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Prophet forecast needs at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        if horizon < 1:
            horizon = 1

        yearly_seasonality = ctx.get_param("yearly_seasonality", "auto")
        weekly_seasonality = ctx.get_param("weekly_seasonality", "auto")
        changepoint_prior_scale = float(
            ctx.get_param("changepoint_prior_scale", 0.05)
        )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        # Allow param override, else use preset
        changepoint_prior_scale = float(
            ctx.get_param("changepoint_prior_scale", preset_cfg["changepoint_prior_scale"])
        )
        seasonality_prior_scale = preset_cfg["seasonality_prior_scale"]
        n_changepoints = preset_cfg["n_changepoints"]

        # Convert seasonality strings to appropriate values
        def _parse_seasonality(val):
            if isinstance(val, bool):
                return val
            s = str(val).strip().lower()
            if s == "true":
                return True
            elif s == "false":
                return False
            return "auto"

        yearly_seasonality = _parse_seasonality(yearly_seasonality)
        weekly_seasonality = _parse_seasonality(weekly_seasonality)

        use_prophet = _has_prophet()
        backend = "prophet" if use_prophet else "seasonal_naive"

        if not use_prophet:
            warn_list.append(
                "Prophet library not available. Falling back to seasonal naive method. "
                "Install prophet (pip install prophet) for full Prophet support."
            )

        if use_prophet:
            progress_callback("Preparing data for Prophet", 15)
            import pandas as pd
            from prophet import Prophet
            import logging

            # Suppress Prophet's verbose logging
            logging.getLogger("prophet").setLevel(logging.WARNING)
            logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

            # Create DataFrame with ds/y columns
            if ctx.time and len(ctx.time) >= n:
                # Use provided timestamps
                dates = pd.to_datetime(ctx.time[:n], errors="coerce")
                if dates.isna().any():
                    # Fallback to integer-based dates
                    dates = pd.date_range(start="2000-01-01", periods=n, freq="D")
                    warn_list.append(
                        "Could not parse provided timestamps. Using synthetic daily dates."
                    )
            else:
                dates = pd.date_range(start="2000-01-01", periods=n, freq="D")

            df = pd.DataFrame({"ds": dates, "y": clean})

            progress_callback("Fitting Prophet model", 25)

            model = Prophet(
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                changepoint_prior_scale=changepoint_prior_scale,
                seasonality_prior_scale=seasonality_prior_scale,
                n_changepoints=min(n_changepoints, n // 2),
                mcmc_samples=preset_cfg["mcmc_samples"],
            )
            model.fit(df)

            progress_callback("Generating forecasts", 60)

            # Infer frequency for future dataframe
            freq = pd.infer_freq(dates)
            if freq is None:
                freq = "D"
            future = model.make_future_dataframe(periods=horizon, freq=freq)
            forecast_df = model.predict(future)

            # Extract forecast portion
            fc_full = forecast_df.tail(horizon)
            fc_values = fc_full["yhat"].values
            fc_lower = fc_full["yhat_lower"].values
            fc_upper = fc_full["yhat_upper"].values

            # In-sample fitted values
            fitted = forecast_df.head(n)["yhat"].values

            progress_callback("Extracting components", 75)

            # Extract components
            components_data = forecast_df.head(n)
            comp_rows = []
            comp_cols = ["Index", "Trend"]
            has_yearly = "yearly" in forecast_df.columns
            has_weekly = "weekly" in forecast_df.columns

            if has_yearly:
                comp_cols.append("Yearly")
            if has_weekly:
                comp_cols.append("Weekly")

            max_display = min(n, 200)
            step = max(1, n // max_display)
            for i in range(0, n, step):
                row = [i + 1, round(float(components_data["trend"].iloc[i]), 6)]
                if has_yearly:
                    row.append(round(float(components_data["yearly"].iloc[i]), 6))
                if has_weekly:
                    row.append(round(float(components_data["weekly"].iloc[i]), 6))
                comp_rows.append(row)

            components_table = make_table("Components", comp_cols, comp_rows)

            # Changepoints
            n_detected_changepoints = len(model.changepoints) if hasattr(model, "changepoints") else 0

            # Metrics
            residuals = clean - fitted
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            mae = float(np.mean(np.abs(residuals)))
            ss_res = float(np.sum(residuals ** 2))
            ss_tot = float(np.sum((clean - np.mean(clean)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

            model_desc = "Facebook Prophet"

        else:
            # Seasonal naive fallback
            progress_callback("Computing seasonal naive forecast", 30)

            period = _infer_period(ctx.frequency)
            if period is None:
                period = min(12, n // 3) if n >= 6 else 1

            fc_values, fc_lower, fc_upper, std_resid = _seasonal_naive_forecast(
                clean, horizon, period
            )

            # In-sample "fitted" values via seasonal lag
            fitted = np.full(n, np.nan)
            for i in range(period, n):
                fitted[i] = clean[i - period]
            # Fill initial values with mean
            for i in range(min(period, n)):
                fitted[i] = np.mean(clean)

            residuals = clean - fitted
            valid_mask = ~np.isnan(residuals)
            rmse = float(np.sqrt(np.mean(residuals[valid_mask] ** 2)))
            mae = float(np.mean(np.abs(residuals[valid_mask])))
            ss_res = float(np.sum(residuals[valid_mask] ** 2))
            ss_tot = float(np.sum((clean[valid_mask] - np.mean(clean[valid_mask])) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

            components_table = make_table(
                "Components", ["Note"],
                [["Seasonal naive fallback does not produce component decomposition. "
                  "Install Prophet for full decomposition."]]
            )
            n_detected_changepoints = 0
            model_desc = f"Seasonal Naive (period={period})"

        progress_callback("Building output", 90)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc_values[i]), 6),
                round(float(fc_lower[i]), 6),
                round(float(fc_upper[i]), 6),
            ])
        fc_table = make_table(
            "Forecast", ["Step", "Forecast", "Lower", "Upper"], fc_rows
        )

        # Model summary
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["Observations", n],
            ["Horizon", horizon],
            ["Changepoint Prior Scale", changepoint_prior_scale],
            ["Yearly Seasonality", str(yearly_seasonality)],
            ["Weekly Seasonality", str(weekly_seasonality)],
            ["Detected Changepoints", n_detected_changepoints],
            ["RMSE (in-sample)", round(rmse, 4)],
            ["MAE (in-sample)", round(mae, 4)],
            ["R-squared (in-sample)", round(r2, 4)],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [fc_table, summary_table, components_table]

        if r2 < 0:
            warn_list.append(
                "Negative R-squared on in-sample data. The model may be a poor fit."
            )
        if horizon > n:
            warn_list.append(
                f"Forecast horizon ({horizon}) exceeds series length ({n}). "
                "Long-range Prophet forecasts rely heavily on trend extrapolation."
            )

        plain_english = (
            f"Prophet forecast for '{name}' ({n} observations) using {backend}. "
            f"Changepoint prior scale={changepoint_prior_scale}. "
            f"In-sample RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast with uncertainty intervals produced."
        )

        charting = (
            "Line chart with original series, fitted values, and forecast with "
            "shaded confidence interval. "
            "If Prophet backend, show component plots (trend, yearly, weekly). "
            "Highlight detected changepoints on the trend line."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "backend": backend,
                "changepoint_prior_scale": changepoint_prior_scale,
                "yearly_seasonality": str(yearly_seasonality),
                "weekly_seasonality": str(weekly_seasonality),
                "n_detected_changepoints": n_detected_changepoints,
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "r2": round(r2, 4),
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Prophet forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=10).",
                "Install prophet (pip install prophet) for full support.",
                "Try adjusting changepoint_prior_scale if the trend is overfitting.",
            ],
        )
