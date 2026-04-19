"""
Kalman Filter / Smoother for Time Series Lab.

Fits an Unobserved Components Model (UCM) via statsmodels UnobservedComponents,
which uses the Kalman filter for estimation and the Kalman smoother for extracting
latent components (level, trend, seasonal, cycle, irregular).
"""

import numpy as np
import pandas as pd
import warnings as _warnings
from statsmodels.tsa.statespace.structural import UnobservedComponents

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _prepare_series(values):
    """Strip edge NaN (UCM handles interior NaN natively via the Kalman filter).

    Returns (trimmed_values, nan_count, first_idx, last_idx) where first_idx and
    last_idx are the inclusive slice bounds into the original array. Callers
    need them to trim the time axis in lockstep so the DatetimeIndex remains
    aligned with the fitted series — see §4.1 of the design mandate (the wrapper
    owns alignment).
    """
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([]), 0, 0, -1
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    return trimmed, nan_count, first, last


def _build_forecast_time_axis(last_time_label, frequency: str, horizon: int):
    """Extend the input's DatetimeIndex by `horizon` steps at the detected
    frequency. Falls back to string labels ``t+1..t+h`` if the last input
    label can't be parsed as a date or the frequency is unknown.
    """
    # Frequency aliases: prefer pandas 2.2+ codes ("YE-DEC", "QE-DEC", "ME");
    # fall back to the legacy codes on older pandas via a second attempt.
    freq_map_modern = {
        "A": "YE-DEC", "ANNUAL": "YE-DEC", "Y": "YE-DEC",
        "Q": "QE-DEC", "QUARTERLY": "QE-DEC", "QS": "QS",
        "M": "ME", "MONTHLY": "ME", "MS": "MS",
        "W": "W", "WEEKLY": "W",
        "D": "D", "DAILY": "D", "B": "B",
        "H": "h", "HOURLY": "h",
    }
    freq_map_legacy = {
        "A": "A-DEC", "ANNUAL": "A-DEC", "Y": "A-DEC",
        "Q": "Q-DEC", "QUARTERLY": "Q-DEC", "QS": "QS",
        "M": "M", "MONTHLY": "M", "MS": "MS",
        "W": "W", "WEEKLY": "W",
        "D": "D", "DAILY": "D", "B": "B",
        "H": "H", "HOURLY": "H",
    }
    key = (frequency or "").strip().upper()
    modern = freq_map_modern.get(key)
    legacy = freq_map_legacy.get(key)
    if modern is None and legacy is None:
        return [f"t+{i + 1}" for i in range(horizon)]
    try:
        last_ts = pd.to_datetime(str(last_time_label))
    except Exception:
        return [f"t+{i + 1}" for i in range(horizon)]
    for code in (modern, legacy):
        if code is None:
            continue
        try:
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore", FutureWarning)
                dates = pd.date_range(start=last_ts, periods=horizon + 1, freq=code)[1:]
            return [d.strftime("%Y-%m-%d") for d in dates]
        except (ValueError, TypeError):
            continue
    return [f"t+{i + 1}" for i in range(horizon)]


def _infer_period(ctx):
    """Infer seasonal period."""
    user = ctx.get_param("seasonal_period") or ctx.get_param("period")
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
    Fit an Unobserved Components Model with Kalman filtering/smoothing.

    Parameters (via ctx.params)
    ---------------------------
    level : str or bool, optional
        Level component: 'local level' (default), 'local linear trend',
        'smooth trend', 'random walk', 'fixed intercept', or True/False.
    trend : bool, optional
        Whether to include a stochastic trend in addition to level. Default False.
    seasonal : int or None, optional
        Seasonal period (None = no seasonal). Auto-detected if omitted.
    cycle : bool, optional
        Whether to include a stochastic cycle component. Default False.
    damped_cycle : bool, optional
        Whether the cycle is damped. Default True.
    stochastic_level : bool, optional
        Default True.
    stochastic_trend : bool, optional
        Default True.
    stochastic_seasonal : bool, optional
        Default True.
    stochastic_cycle : bool, optional
        Default True.
    horizon : int, optional
        Forecast steps. Default 10.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_nan, first_idx, last_idx = _prepare_series(values)
        n = len(clean)
        # Trim the time axis in lockstep with the value trim so the
        # DatetimeIndex stays aligned with `clean` regardless of edge-NaN
        # behavior. This is the source-of-truth for every output "Time"
        # column per §4.1 of the design mandate.
        if ctx.time and len(ctx.time) >= last_idx + 1 and last_idx >= first_idx:
            time_axis = list(ctx.time[first_idx:last_idx + 1])
        else:
            time_axis = list(range(1, n + 1))
        if n_nan > 0:
            warn_list.append(
                f"{n_nan} missing values present. The Kalman filter handles these "
                "natively by increasing uncertainty during missing periods."
            )

        non_nan = int(np.sum(~np.isnan(clean)))
        if non_nan < 10:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {non_nan} non-missing observations. Need at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))

        # Model specification
        level_param = ctx.get_param("level", "local level")
        trend_param = ctx.get_param("trend", False)
        cycle_param = ctx.get_param("cycle", False)
        damped_cycle = ctx.get_param("damped_cycle", True)

        stoch_level = ctx.get_param("stochastic_level", True)
        stoch_trend = ctx.get_param("stochastic_trend", True)
        stoch_seasonal = ctx.get_param("stochastic_seasonal", True)
        stoch_cycle = ctx.get_param("stochastic_cycle", True)

        # Seasonal
        period = _infer_period(ctx)
        seasonal_param = ctx.get_param("seasonal")
        if seasonal_param is not None:
            if isinstance(seasonal_param, bool):
                seasonal = period if seasonal_param and period and period >= 2 and non_nan >= 2 * period else None
            else:
                seasonal = int(seasonal_param)
        elif period and period >= 2 and non_nan >= 2 * period:
            seasonal = period
        else:
            seasonal = None

        progress_callback("Building UCM specification", 15)

        # Determine level specification
        if isinstance(level_param, bool):
            if level_param:
                level_spec = "local level"
            else:
                level_spec = None
        elif isinstance(level_param, str):
            level_spec = level_param.lower().strip()
            valid_levels = [
                "local level", "local linear trend", "smooth trend",
                "random walk", "fixed intercept", "deterministic constant",
                "local linear deterministic trend", "random walk with drift",
                "deterministic trend",
            ]
            if level_spec not in valid_levels:
                warn_list.append(f"Unknown level '{level_spec}'. Using 'local level'.")
                level_spec = "local level"
        else:
            level_spec = "local level"

        progress_callback("Fitting UCM via Kalman filter", 25)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                model = UnobservedComponents(
                    clean,
                    level=level_spec,
                    trend=trend_param,
                    seasonal=seasonal,
                    cycle=cycle_param,
                    damped_cycle=damped_cycle if cycle_param else False,
                    stochastic_level=stoch_level,
                    stochastic_trend=stoch_trend if trend_param else False,
                    stochastic_seasonal=stoch_seasonal if seasonal else False,
                    stochastic_cycle=stoch_cycle if cycle_param else False,
                )
                fit = model.fit(disp=False, maxiter=500)
            except np.linalg.LinAlgError:
                warn_list.append("Singular matrix during estimation. Trying simpler specification.")
                model = UnobservedComponents(
                    clean,
                    level="local level",
                    trend=False,
                    seasonal=seasonal,
                    cycle=False,
                    stochastic_level=True,
                    stochastic_seasonal=stoch_seasonal if seasonal else False,
                )
                fit = model.fit(disp=False, maxiter=500)
                level_spec = "local level"
                trend_param = False
                cycle_param = False
            except Exception as e1:
                warn_list.append(f"Model fitting failed ({e1}). Trying local level only.")
                model = UnobservedComponents(clean, level="local level")
                fit = model.fit(disp=False, maxiter=500)
                level_spec = "local level"
                trend_param = False
                seasonal = None
                cycle_param = False

        progress_callback("Extracting smoothed components", 50)

        # Smoothed state
        smoothed = fit.smoothed_state
        # Components from the model
        # The available components depend on the specification
        components = {}

        # Level
        try:
            level_comp = fit.level.smoothed
            if hasattr(level_comp, 'values'):
                level_comp = level_comp.values
            components["Level"] = np.asarray(level_comp)
        except Exception:
            pass

        # Trend
        if trend_param:
            try:
                trend_comp = fit.trend.smoothed
                if hasattr(trend_comp, 'values'):
                    trend_comp = trend_comp.values
                components["Trend"] = np.asarray(trend_comp)
            except Exception:
                pass

        # Seasonal
        if seasonal:
            try:
                seas_comp = fit.seasonal.smoothed
                if hasattr(seas_comp, 'values'):
                    seas_comp = seas_comp.values
                components["Seasonal"] = np.asarray(seas_comp)
            except Exception:
                pass

        # Cycle
        if cycle_param:
            try:
                cycle_comp = fit.cycle.smoothed
                if hasattr(cycle_comp, 'values'):
                    cycle_comp = cycle_comp.values
                components["Cycle"] = np.asarray(cycle_comp)
            except Exception:
                pass

        # Residuals
        resid = fit.resid
        resid_arr = resid.values if hasattr(resid, 'values') else np.asarray(resid)

        # Filtered values (one-step-ahead predictions)
        filt = fit.fittedvalues
        filt_arr = filt.values if hasattr(filt, 'values') else np.asarray(filt)

        progress_callback("Generating forecasts", 65)

        # Forecast
        try:
            fc_obj = fit.get_forecast(steps=horizon, alpha=0.05)
            fc = fc_obj.predicted_mean
            fc_arr = fc.values if hasattr(fc, 'values') else np.asarray(fc)
            ci = fc_obj.conf_int()
            lower = ci.iloc[:, 0].values if hasattr(ci, 'iloc') else ci[:, 0]
            upper = ci.iloc[:, 1].values if hasattr(ci, 'iloc') else ci[:, 1]
        except Exception as ef:
            warn_list.append(f"Forecasting failed ({ef}). No forecast produced.")
            fc_arr = np.array([])
            lower = np.array([])
            upper = np.array([])

        progress_callback("Building output", 80)

        # Components table. `time_axis` is the source of truth — already
        # trimmed in lockstep with `clean` — so every row's "Time" cell lines
        # up with the observation it describes. statsmodels result arrays
        # (smoothed_state, fittedvalues, resid) vary between ndarray and
        # Series across versions; we normalized them to ndarrays above and
        # never touch `.index` on them. The output DataFrame's index is
        # `time_axis`, not whatever statsmodels returned.
        comp_cols = ["Time", name, "Filtered"] + list(components.keys()) + ["Residual"]
        step = max(1, n // 500) if ctx.preset == "Fast" else max(1, n // 1000)
        comp_rows = []
        for i in range(0, n, step):
            row = [
                time_axis[i],
                None if np.isnan(clean[i]) else float(clean[i]),
                float(filt_arr[i]) if i < len(filt_arr) and not np.isnan(filt_arr[i]) else None,
            ]
            for comp_arr in components.values():
                val = comp_arr[i] if i < len(comp_arr) else None
                row.append(float(val) if val is not None and not np.isnan(val) else None)
            row.append(float(resid_arr[i]) if i < len(resid_arr) and not np.isnan(resid_arr[i]) else None)
            comp_rows.append(row)

        comp_table = make_table("Smoothed Components", comp_cols, comp_rows)

        # Forecast table — extend the DatetimeIndex from the last input date
        # at the detected frequency for `horizon` steps.
        tables = [comp_table]
        if len(fc_arr) > 0:
            fc_time_axis = _build_forecast_time_axis(
                time_axis[-1] if time_axis else None, ctx.frequency, len(fc_arr)
            )
            fc_rows = []
            for i in range(len(fc_arr)):
                fc_rows.append([
                    fc_time_axis[i],
                    round(float(fc_arr[i]), 6),
                    round(float(lower[i]), 6),
                    round(float(upper[i]), 6),
                ])
            fc_table = make_table(
                "Forecast", ["Time", "Forecast", "Lower 95%", "Upper 95%"], fc_rows
            )
            tables.append(fc_table)

        # Model parameters. `fit.params` and `fit.bse` come back as ndarray
        # when the model was fit on a numpy array (which we do here) and as
        # pandas.Series when fit on a pandas Series. `fit.param_names` is a
        # plain list in both cases — use it as the source of names and index
        # the values positionally. This avoids the earlier crash where
        # `fit.params.index` raised AttributeError on ndarray.
        param_names = list(getattr(fit, "param_names", []) or [])
        params_arr = np.asarray(fit.params)
        try:
            bse_arr = np.asarray(fit.bse)
        except Exception:
            bse_arr = None

        param_rows = []
        for i, pname in enumerate(param_names):
            if i >= len(params_arr):
                break
            pval = float(params_arr[i])
            se = None
            if bse_arr is not None and i < len(bse_arr):
                try:
                    se_val = float(bse_arr[i])
                    if not np.isnan(se_val) and not np.isinf(se_val):
                        se = se_val
                except Exception:
                    se = None
            param_rows.append([str(pname), round(pval, 6), round(se, 6) if se is not None else None])

        param_table = make_table(
            "Estimated Parameters",
            ["Parameter", "Estimate", "Std Error"],
            param_rows,
        )
        tables.append(param_table)

        # Model diagnostics
        aic = float(fit.aic)
        bic = float(fit.bic)
        llf = float(fit.llf)
        valid_resid = resid_arr[~np.isnan(resid_arr)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        diag_rows = [
            ["Level Specification", level_spec or "None"],
            ["Trend", str(trend_param)],
            ["Seasonal Period", seasonal if seasonal else "None"],
            ["Cycle", str(cycle_param)],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["Log-Likelihood", round(llf, 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Observations", n],
            ["Missing Values", n_nan],
            ["Forecast Horizon", horizon],
        ]

        # Ljung-Box on residuals
        if len(valid_resid) > 15:
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox
                lb = acorr_ljungbox(valid_resid, lags=[min(10, len(valid_resid) // 3)], return_df=True)
                for _, row in lb.iterrows():
                    diag_rows.append([
                        f"Ljung-Box Lag {int(row.name)}",
                        f"Q={round(row['lb_stat'], 4)}, p={round(row['lb_pvalue'], 6)}"
                    ])
                    if row['lb_pvalue'] < 0.05:
                        warn_list.append(
                            f"Residual autocorrelation at lag {int(row.name)} (p={row['lb_pvalue']:.4f}). "
                            "Model may be under-specified."
                        )
            except Exception:
                pass

        diag_table = make_table("Model Diagnostics", ["Metric", "Value"], diag_rows)
        tables.append(diag_table)

        # Plain English
        model_parts = [f"level='{level_spec}'"]
        if trend_param:
            model_parts.append("stochastic trend")
        if seasonal:
            model_parts.append(f"seasonal (period={seasonal})")
        if cycle_param:
            model_parts.append("cycle" + (" (damped)" if damped_cycle else ""))
        model_desc = ", ".join(model_parts)

        plain = (
            f"Unobserved Components Model ({model_desc}) fitted to '{name}' "
            f"({n} observations) via Kalman filter/smoother. "
            f"AIC={aic:.1f}"
        )
        if rmse:
            plain += f", RMSE={rmse:.4f}"
        plain += "."
        if n_nan > 0:
            plain += f" {n_nan} missing values were handled natively by the Kalman filter."
        if len(fc_arr) > 0:
            plain += f" {horizon}-step forecast produced with 95% confidence intervals."

        if components:
            # Report dominant component
            comp_vars = {k: float(np.nanvar(v)) for k, v in components.items()}
            dominant = max(comp_vars, key=comp_vars.get)
            plain += f" The '{dominant}' component has the largest variance."

        charting = (
            "Multi-panel chart: Original + Filtered overlay on top, then each "
            "smoothed component (Level, Trend, Seasonal, Cycle) in separate panels. "
            "Forecast continuation with shaded confidence interval on the original panel."
        )

        progress_callback("Done", 100)

        audit = {
            "level": level_spec,
            "trend": trend_param,
            "seasonal_period": seasonal,
            "cycle": cycle_param,
            "aic": round(aic, 2),
            "bic": round(bic, 2),
            "rmse": round(rmse, 4) if rmse else None,
            "horizon": horizon,
            "n_missing": n_nan,
        }

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Kalman filter model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try a simpler specification (level='local level', no trend/cycle).",
                "Check that the seasonal period is appropriate.",
                "For convergence issues, try 'fixed intercept' or 'random walk' level.",
            ],
        )
