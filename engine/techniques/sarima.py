"""
SARIMA (Seasonal ARIMA) modelling for Time Series Lab.

Fits a SARIMAX model with user-specified or preset-guided orders and produces
point forecasts with confidence intervals.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.statespace.sarimax import SARIMAX

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
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


def _infer_m(ctx):
    """Infer seasonal period m."""
    m = ctx.get_param("m")
    if m is not None:
        return int(m)
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24,
    }
    freq = (ctx.frequency or "").strip().upper()
    return freq_map.get(freq, 12)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a SARIMA model and produce forecasts.

    Parameters (via ctx.params)
    ---------------------------
    order : list[int]
        [p, d, q]. Default [1, 1, 1].
    seasonal_order : list[int]
        [P, D, Q, m]. Default [1, 1, 1, m] where m is inferred.
    m : int, optional
        Seasonal period override (also settable as seasonal_order[3]).
    horizon : int, optional
        Forecast steps. Default 10.
    trend : str, optional
        'n', 'c', 't', 'ct'. Default 'n'.
    enforce_stationarity : bool, optional
        Default True.
    enforce_invertibility : bool, optional
        Default True.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 12:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. SARIMA needs at least 12.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        # Parse orders. Fix B Tier 1a: order/seasonal_order arrive as catalog
        # STRINGS; the shared helper parses string|list|tuple (the prior
        # list-only parse silently DROPPED a dialog-typed order to the default).
        # seasonal_order blank -> (1,1,1,m_inferred): the frequency-aware default
        # is preserved byte-identical; an explicit P,D,Q,m is honored. m>1 guard.
        from techniques._validation import ParamError, parse_int_tuple, check_seasonal
        m = _infer_m(ctx)
        try:
            order = parse_int_tuple(ctx.get_param("order"), 3, "SARIMA Order",
                                    default=(1, 1, 1))
            seasonal_order = parse_int_tuple(
                ctx.get_param("seasonal_order"), 4, "Seasonal Order",
                default=(1, 1, 1, m),
            )
            check_seasonal(P=seasonal_order[0], D=seasonal_order[1],
                           Q=seasonal_order[2], m=seasonal_order[3])
        except ParamError as e:
            return make_error_response(ctx, str(e), error_fixes=e.fixes)

        # Validate: need enough data for seasonal differencing
        min_obs = seasonal_order[3] * (seasonal_order[1] + 1) + order[1] + max(order[0], seasonal_order[0] * seasonal_order[3])
        if n < min_obs + 10:
            warn_list.append(
                f"Series may be too short (n={n}) for SARIMA{order}x{seasonal_order}. "
                "Model may fail or produce unreliable results."
            )

        trend_param = ctx.get_param("trend", "n")
        enforce_stat = ctx.get_param("enforce_stationarity", True)
        enforce_inv = ctx.get_param("enforce_invertibility", True)

        progress_callback("Fitting SARIMA model", 20)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                model = SARIMAX(
                    clean,
                    order=order,
                    seasonal_order=seasonal_order,
                    trend=trend_param,
                    enforce_stationarity=enforce_stat,
                    enforce_invertibility=enforce_inv,
                )
                fit = model.fit(disp=False, maxiter=200)
            except np.linalg.LinAlgError:
                warn_list.append(
                    "Singular matrix during estimation. Retrying without stationarity enforcement."
                )
                model = SARIMAX(
                    clean,
                    order=order,
                    seasonal_order=seasonal_order,
                    trend=trend_param,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = model.fit(disp=False, maxiter=200)
            except Exception as e:
                # Try simpler model
                warn_list.append(f"SARIMA{order}x{seasonal_order} failed ({e}). Trying (1,1,0)x(1,1,0,{seasonal_order[3]}).")
                order = (1, 1, 0)
                seasonal_order = (1, 1, 0, seasonal_order[3])
                model = SARIMAX(
                    clean,
                    order=order,
                    seasonal_order=seasonal_order,
                    trend="n",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = model.fit(disp=False, maxiter=200)

        if not fit.mle_retvals.get("converged", True) if hasattr(fit, 'mle_retvals') and isinstance(getattr(fit, 'mle_retvals', None), dict) else False:
            warn_list.append("MLE optimization did not converge. Results may be unreliable.")

        progress_callback("Generating forecasts", 55)

        forecast_obj = fit.get_forecast(steps=horizon)
        fc = forecast_obj.predicted_mean.values if hasattr(forecast_obj.predicted_mean, 'values') else np.asarray(forecast_obj.predicted_mean)
        ci_df = forecast_obj.conf_int()
        lower = ci_df.iloc[:, 0].values if hasattr(ci_df, 'iloc') else ci_df[:, 0]
        upper = ci_df.iloc[:, 1].values if hasattr(ci_df, 'iloc') else ci_df[:, 1]

        fitted_vals = fit.fittedvalues
        fitted_arr = fitted_vals.values if hasattr(fitted_vals, 'values') else np.asarray(fitted_vals)
        if len(fitted_arr) < n:
            fitted_arr = np.concatenate([np.full(n - len(fitted_arr), np.nan), fitted_arr])
        residuals = clean - fitted_arr

        progress_callback("Building output", 80)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc[i]), 6),
                round(float(lower[i]), 6),
                round(float(upper[i]), 6),
            ])
        forecast_table = make_table(
            "SARIMA Forecast", ["Step", "Forecast", "Lower 95%", "Upper 95%"], fc_rows
        )

        # Fitted values
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        fit_rows = []
        for i in range(n):
            fit_rows.append([
                time_col[i],
                clean[i],
                float(fitted_arr[i]) if not np.isnan(fitted_arr[i]) else None,
                float(residuals[i]) if not np.isnan(residuals[i]) else None,
            ])
        fitted_table = make_table("Fitted Values", ["Time", name, "Fitted", "Residual"], fit_rows)

        # Model diagnostics
        aic = float(fit.aic)
        bic = float(fit.bic)
        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        order_str = f"({order[0]},{order[1]},{order[2]})"
        seas_str = f"({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]},{seasonal_order[3]})"

        summary_rows = [
            ["Order (p,d,q)", order_str],
            ["Seasonal Order (P,D,Q,m)", seas_str],
            ["Trend", trend_param],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["Observations", n],
            ["Forecast Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Residual diagnostics
        progress_callback("Residual diagnostics", 90)
        diag_rows = []
        if len(valid_resid) > 1:
            diag_rows.append(["Residual Mean", round(float(np.mean(valid_resid)), 6)])
            diag_rows.append(["Residual Std", round(float(np.std(valid_resid, ddof=1)), 6)])
        if len(valid_resid) > 10:
            try:
                from scipy import stats as sp_stats
                jb_stat, jb_p = sp_stats.jarque_bera(valid_resid)
                diag_rows.append(["Jarque-Bera Stat", round(float(jb_stat), 4)])
                diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
                if jb_p < 0.05:
                    warn_list.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")
            except Exception:
                pass
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox
                lb = acorr_ljungbox(valid_resid, lags=[min(10, len(valid_resid) // 3)], return_df=True)
                for _, row in lb.iterrows():
                    lag = int(row.name)
                    diag_rows.append([f"Ljung-Box Lag {lag}", f"Q={round(row['lb_stat'], 4)}, p={round(row['lb_pvalue'], 6)}"])
                    if row['lb_pvalue'] < 0.05:
                        warn_list.append(f"Residual autocorrelation at lag {lag} (p={row['lb_pvalue']:.4f}).")
            except Exception:
                pass

        diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

        # Plain English
        plain = (
            f"SARIMA{order_str}x{seas_str} fitted to '{name}' ({n} obs). "
            f"AIC={aic:.1f}"
        )
        if rmse:
            plain += f", RMSE={rmse:.4f}"
        plain += f". {horizon}-step forecast produced."

        charting = (
            "Line chart with original series, fitted overlay, and forecast with "
            "shaded 95% confidence interval. Second panel: residuals."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[forecast_table, fitted_table, summary_table, diag_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "order": order_str,
                "seasonal_order": seas_str,
                "trend": trend_param,
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "rmse": round(rmse, 4) if rmse else None,
                "horizon": horizon,
                **format_significance_disclosure(
                    test_name="SARIMA MLE t-tests + Ljung-Box residual diagnostic",
                    critical_value_formula=(
                        "statsmodels SARIMAX standard errors; two-sided "
                        "t-tests at α; Ljung-Box via acorr_ljungbox"
                    ),
                    ac_corrected=True,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"SARIMA failed: {e}",
            error_fixes=[
                "Check that order and seasonal_order are valid.",
                "Ensure the series is long enough for the specified seasonal period.",
                "Try reducing the order or seasonal order.",
                "For non-stationary series, ensure d >= 1 or D >= 1.",
            ],
        )
