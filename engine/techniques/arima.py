"""
ARIMA / Auto-ARIMA forecasting for Time Series Lab.

Handles both technique_ids: "arima" (user-specified order) and "auto_arima"
(automatic order selection via pmdarima).
"""

import numpy as np
import pmdarima as pm
from statsmodels.tsa.arima.model import ARIMA

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit an ARIMA model and produce forecasts.

    Parameters (via ctx.params)
    ---------------------------
    For auto_arima:
        horizon : int
            Number of steps to forecast. Default 10.
        seasonal : bool
            Whether to fit seasonal ARIMA. Default False.
        m : int
            Seasonal period (required if seasonal=True).
        d : int, optional
            Fixed differencing order. None = auto.
        max_p, max_q, max_d : int, optional
            Upper bounds for auto search.
        information_criterion : str
            'aic' (default), 'bic', 'hqic', 'oob'.

    For arima (manual):
        order : list[int]
            [p, d, q]. Required.
        seasonal_order : list[int], optional
            [P, D, Q, m]. Default [0,0,0,0].
        horizon : int
            Steps to forecast. Default 10.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warnings = []

        # Prepare series: strip edge NaN, interpolate interior
        clean, n_interpolated = _prepare_series(values)
        n = len(clean)
        if n_interpolated > 0:
            warnings.append(
                f"{n_interpolated} interior missing values were linearly interpolated."
            )

        if n < 10:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "ARIMA needs at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1
        if horizon > n:
            warnings.append(
                f"Forecast horizon ({horizon}) exceeds series length ({n}). "
                "Long-range forecasts may be unreliable."
            )

        is_auto = ctx.technique_id in ("auto_arima", "auto-arima")

        if is_auto:
            result = _run_auto_arima(ctx, clean, name, horizon, warnings, progress_callback)
        else:
            result = _run_manual_arima(ctx, clean, name, horizon, warnings, progress_callback)

        return result

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"ARIMA failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with no text values.",
                "Check for constant series (ARIMA cannot model zero-variance data).",
                "Try differencing the series first if it is non-stationary.",
                "For auto_arima, try setting seasonal=False if the search is too slow.",
            ],
        )


def _run_auto_arima(ctx, clean, name, horizon, warnings, progress_callback):
    """Use pmdarima auto_arima to find the best order."""
    progress_callback("Searching for optimal ARIMA order", 15)

    seasonal = ctx.get_param("seasonal", False)
    m = int(ctx.get_param("m", 1))
    if seasonal and m <= 1:
        warnings.append("seasonal=True but m=1. Setting m based on frequency or defaulting to 12.")
        m = _infer_m(ctx.frequency)

    d = ctx.get_param("d", None)
    if d is not None:
        d = int(d)

    ic = ctx.get_param("information_criterion", "aic")

    preset_config = {
        "Fast": {"max_p": 2, "max_q": 2, "max_d": 1, "max_P": 1, "max_Q": 1, "max_D": 1, "stepwise": True},
        "Balanced": {"max_p": 5, "max_q": 5, "max_d": 2, "max_P": 2, "max_Q": 2, "max_D": 1, "stepwise": True},
        "Thorough": {"max_p": 7, "max_q": 7, "max_d": 2, "max_P": 2, "max_Q": 2, "max_D": 2, "stepwise": False},
    }
    cfg = preset_config.get(ctx.preset, preset_config["Balanced"])

    # Allow user overrides
    max_p = int(ctx.get_param("max_p", cfg["max_p"]))
    max_q = int(ctx.get_param("max_q", cfg["max_q"]))
    max_d = int(ctx.get_param("max_d", cfg["max_d"]))

    progress_callback("Fitting auto_arima (this may take a moment)", 25)

    model = pm.auto_arima(
        clean,
        d=d,
        max_p=max_p,
        max_q=max_q,
        max_d=max_d,
        seasonal=seasonal,
        m=m if seasonal else 1,
        max_P=cfg["max_P"] if seasonal else 0,
        max_Q=cfg["max_Q"] if seasonal else 0,
        max_D=cfg["max_D"] if seasonal else 0,
        stepwise=cfg["stepwise"],
        information_criterion=ic,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )

    progress_callback("Generating forecasts", 70)

    order = model.order
    seasonal_order = model.seasonal_order

    # Forecasts with confidence intervals
    fc, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=0.05)

    # In-sample fitted values and residuals
    fitted = model.predict_in_sample()
    residuals = clean - fitted

    return _build_output(
        ctx, name, clean, order, seasonal_order, model.aic(), model.bic(),
        fc, conf_int, fitted, residuals, horizon, warnings, progress_callback,
        extra_audit={"method": "auto_arima", "ic": ic, "stepwise": cfg["stepwise"]},
    )


def _run_manual_arima(ctx, clean, name, horizon, warnings, progress_callback):
    """Fit ARIMA with user-specified order."""
    progress_callback("Parsing ARIMA order", 15)

    order_param = ctx.get_param("order")
    if order_param is None:
        return make_error_response(
            ctx,
            "The 'order' parameter [p, d, q] is required for manual ARIMA.",
            error_fixes=[
                "Provide order=[p, d, q], e.g. order=[1, 1, 1].",
                "Or use the 'auto_arima' technique for automatic selection.",
            ],
        )

    if isinstance(order_param, (list, tuple)) and len(order_param) == 3:
        order = tuple(int(x) for x in order_param)
    else:
        return make_error_response(
            ctx,
            f"'order' must be a list of 3 integers [p, d, q], got: {order_param}",
            error_fixes=["Example: order=[1, 1, 1] for ARIMA(1,1,1)."],
        )

    seasonal_order_param = ctx.get_param("seasonal_order", [0, 0, 0, 0])
    if isinstance(seasonal_order_param, (list, tuple)) and len(seasonal_order_param) == 4:
        seasonal_order = tuple(int(x) for x in seasonal_order_param)
    else:
        seasonal_order = (0, 0, 0, 0)

    progress_callback("Fitting ARIMA model", 30)

    model = ARIMA(clean, order=order, seasonal_order=seasonal_order)
    fit = model.fit()

    progress_callback("Generating forecasts", 65)

    # Forecast
    forecast_result = fit.get_forecast(steps=horizon, alpha=0.05)
    fc = forecast_result.predicted_mean
    conf_int_df = forecast_result.conf_int()
    conf_int = np.column_stack([conf_int_df.iloc[:, 0].values, conf_int_df.iloc[:, 1].values])

    # In-sample
    fitted = fit.fittedvalues
    # fittedvalues may be shorter than clean by d due to differencing
    if len(fitted) < len(clean):
        pad = np.full(len(clean) - len(fitted), np.nan)
        fitted = np.concatenate([pad, fitted])
    residuals = clean - fitted

    return _build_output(
        ctx, name, clean, order, seasonal_order, fit.aic, fit.bic,
        fc, conf_int, fitted, residuals, horizon, warnings, progress_callback,
        extra_audit={"method": "manual"},
    )


def _build_output(ctx, name, clean, order, seasonal_order, aic, bic,
                   fc, conf_int, fitted, residuals, horizon, warnings,
                   progress_callback, extra_audit=None):
    """Assemble tables and response from fitted ARIMA results."""
    progress_callback("Building output tables", 80)

    n = len(clean)

    # Forecast table
    fc_rows = []
    for i in range(horizon):
        fc_rows.append([
            n + i + 1,
            round(float(fc[i]), 6),
            round(float(conf_int[i, 0]), 6),
            round(float(conf_int[i, 1]), 6),
        ])
    forecast_table = make_table(
        "Forecast",
        ["Step", "Forecast", "Lower 95%", "Upper 95%"],
        fc_rows,
    )

    # Fitted values table (include original + fitted + residual)
    time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
    fitted_rows = []
    for i in range(n):
        fitted_rows.append([
            time_col[i],
            clean[i],
            float(fitted[i]) if not np.isnan(fitted[i]) else None,
            float(residuals[i]) if not np.isnan(residuals[i]) else None,
        ])
    fitted_table = make_table(
        "Fitted Values",
        ["Time", name, "Fitted", "Residual"],
        fitted_rows,
    )

    # Model summary table
    order_str = f"({order[0]},{order[1]},{order[2]})"
    seas_str = f"({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]},{seasonal_order[3]})"
    valid_resid = residuals[~np.isnan(residuals)]
    rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
    mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

    summary_rows = [
        ["Order (p,d,q)", order_str],
        ["Seasonal Order (P,D,Q,m)", seas_str],
        ["AIC", round(float(aic), 2)],
        ["BIC", round(float(bic), 2)],
        ["RMSE", round(rmse, 4) if rmse else None],
        ["MAE", round(mae, 4) if mae else None],
        ["Observations", n],
        ["Forecast Horizon", horizon],
    ]
    summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

    # Residual diagnostics
    progress_callback("Residual diagnostics", 90)
    if len(valid_resid) > 10:
        from scipy import stats
        jb_stat, jb_p = stats.jarque_bera(valid_resid)
        lb_results = _ljung_box(valid_resid, lags=min(10, len(valid_resid) // 3))
    else:
        jb_stat, jb_p = None, None
        lb_results = []

    diag_rows = [
        ["Residual Mean", round(float(np.nanmean(valid_resid)), 6) if len(valid_resid) > 0 else None],
        ["Residual Std", round(float(np.nanstd(valid_resid, ddof=1)), 6) if len(valid_resid) > 1 else None],
    ]
    if jb_stat is not None:
        diag_rows.append(["Jarque-Bera Statistic", round(float(jb_stat), 4)])
        diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
        if jb_p < 0.05:
            warnings.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")
    for lag, lb_stat, lb_p in lb_results:
        diag_rows.append([f"Ljung-Box Lag {lag}", f"Q={round(lb_stat, 4)}, p={round(lb_p, 6)}"])
        if lb_p < 0.05:
            warnings.append(
                f"Residual autocorrelation detected at lag {lag} (Ljung-Box p={lb_p:.4f}). "
                "Model may be under-specified."
            )

    diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

    # Plain English
    plain_english = (
        f"ARIMA{order_str} model fitted to '{name}' ({n} observations). "
    )
    if seasonal_order != (0, 0, 0, 0):
        plain_english += f"Seasonal component: {seas_str}. "
    plain_english += f"AIC={aic:.1f}, RMSE={rmse:.4f}. " if rmse else f"AIC={aic:.1f}. "
    plain_english += f"{horizon}-step forecast produced."

    if rmse and rmse > np.nanstd(clean) * 0.9:
        warnings.append(
            "RMSE is close to the standard deviation of the original series, "
            "suggesting the model may not be much better than a naive forecast."
        )

    charting = (
        "Line chart with the original series, fitted values overlaid, and forecast "
        "continuation with shaded 95% confidence interval. "
        "Secondary panel: residual plot (bar or scatter)."
    )

    progress_callback("Done", 100)

    audit = {
        "order": order_str,
        "seasonal_order": seas_str,
        "aic": round(float(aic), 2),
        "bic": round(float(bic), 2),
        "rmse": round(rmse, 4) if rmse else None,
        "mae": round(mae, 4) if mae else None,
        "horizon": horizon,
        **format_significance_disclosure(
            test_name="ARIMA MLE t-tests + Ljung-Box residual diagnostic",
            critical_value_formula=(
                "statsmodels ARIMA standard errors (hessian/outer-product), "
                "two-sided t-test at α; Ljung-Box via "
                "statsmodels.stats.diagnostic.acorr_ljungbox"
            ),
            ac_corrected=True,
        ),
    }
    if extra_audit:
        audit.update(extra_audit)

    return make_response(
        ctx,
        tables=[forecast_table, fitted_table, summary_table, diag_table],
        plain_english_summary=plain_english,
        warnings=warnings,
        charting_suggestions=charting,
        audit_fields=audit,
    )


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN. Return (clean, n_interpolated)."""
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


def _ljung_box(residuals, lags=10):
    """Run Ljung-Box test at a few lag values. Returns list of (lag, stat, p)."""
    results = []
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb = acorr_ljungbox(residuals, lags=[lags], return_df=True)
        for _, row in lb.iterrows():
            results.append((int(row.name), float(row["lb_stat"]), float(row["lb_pvalue"])))
    except Exception:
        pass
    return results


def _infer_m(frequency):
    """Infer seasonal period m from frequency string."""
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    f = (frequency or "").strip().upper()
    return freq_map.get(f, 12)
