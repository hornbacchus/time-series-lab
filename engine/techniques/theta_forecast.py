"""
Theta Method forecasting for Time Series Lab.

The Theta method decomposes the series into two 'theta lines' (one capturing
the long-run trend and the other the short-run dynamics) and combines their
forecasts. Uses statsmodels ThetaModel.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.forecasting.theta import ThetaModel

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


def _infer_period(ctx):
    """Infer seasonal period for deseasonalization."""
    user = ctx.get_param("period")
    if user is not None:
        return int(user)
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24,
    }
    freq = (ctx.frequency or "").strip().upper()
    return freq_map.get(freq, None)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Theta method forecast on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int, optional
        Number of steps to forecast. Default 10.
    period : int, optional
        Seasonal period for deseasonalization. None = no deseason.
    deseasonalize : bool, optional
        Whether to remove seasonality before applying Theta. Default True if period detected.
    theta : float, optional
        Theta parameter. Default 2.0 (the standard Theta method).
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 8:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. Theta needs at least 8.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        period = _infer_period(ctx)
        deseasonalize = ctx.get_param("deseasonalize", True)
        if period is not None and period >= 2 and n >= 2 * period and deseasonalize:
            use_deseas = True
        else:
            use_deseas = False
            if deseasonalize and period and n < 2 * period:
                warn_list.append(
                    f"Series too short for deseasonalization (n={n}, period={period}). Proceeding without."
                )

        progress_callback("Fitting Theta model", 20)

        import pandas as pd
        series = pd.Series(clean)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                model = ThetaModel(
                    series,
                    period=period if use_deseas else None,
                    deseasonalize=use_deseas,
                )
                fit = model.fit()
            except Exception as e1:
                # Fallback: no deseasonalization
                if use_deseas:
                    warn_list.append(
                        f"Theta with deseasonalization failed ({e1}). Retrying without."
                    )
                    model = ThetaModel(series, deseasonalize=False)
                    fit = model.fit()
                    use_deseas = False
                else:
                    raise

        progress_callback("Generating forecasts", 55)

        fc = fit.forecast(horizon)
        fc_values = fc.values if hasattr(fc, 'values') else np.asarray(fc)

        # Prediction intervals via simulation
        n_sim = {"Fast": 100, "Balanced": 500, "Thorough": 1000}.get(ctx.preset, 500)
        try:
            pi = fit.prediction_intervals(horizon, alpha=0.05)
            lower = pi.iloc[:, 0].values if hasattr(pi, 'iloc') else pi[:, 0]
            upper = pi.iloc[:, 1].values if hasattr(pi, 'iloc') else pi[:, 1]
        except Exception:
            # Fallback: simple interval
            fitted_vals = fit.forecast(0)  # will fail, so use residual-based
            resid_std = np.std(clean[1:] - clean[:-1]) * np.sqrt(np.arange(1, horizon + 1))
            lower = fc_values - 1.96 * resid_std
            upper = fc_values + 1.96 * resid_std
            warn_list.append("Prediction intervals approximated from differenced residual std.")

        progress_callback("Building output", 80)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc_values[i]), 6),
                round(float(lower[i]), 6),
                round(float(upper[i]), 6),
            ])
        forecast_table = make_table(
            "Theta Forecast", ["Step", "Forecast", "Lower 95%", "Upper 95%"], fc_rows
        )

        # Model summary
        summary_rows = [
            ["Method", "Theta"],
            ["Deseasonalized", use_deseas],
            ["Seasonal Period", period if use_deseas else "N/A"],
            ["Observations", n],
            ["Forecast Horizon", horizon],
            ["Preset", ctx.preset],
        ]

        # Try to get b0 (drift) and alpha from the fit
        if hasattr(fit, 'params'):
            for k, v in fit.params.items() if isinstance(fit.params, dict) else []:
                summary_rows.append([f"Param: {k}", round(float(v), 6)])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Plain English
        trend_dir = "upward" if fc_values[-1] > fc_values[0] else "downward" if fc_values[-1] < fc_values[0] else "flat"
        plain = (
            f"Theta method forecast for '{name}' ({n} observations). "
            f"{horizon}-step forecast produced with {trend_dir} trajectory."
        )
        if use_deseas:
            plain += f" Seasonal period {period} removed before forecasting and re-applied."

        charting = (
            "Line chart with original series and forecast continuation with "
            "shaded 95% prediction interval."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[forecast_table, summary_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "method": "theta",
                "deseasonalized": use_deseas,
                "period": period if use_deseas else None,
                "horizon": horizon,
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Theta method failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try setting deseasonalize=False if the seasonal period is incorrect.",
                "Provide a longer series (at least 8 observations).",
            ],
        )
