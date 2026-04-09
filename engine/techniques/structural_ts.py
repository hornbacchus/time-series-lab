"""
Structural Time Series / UCM (Unobserved Components Model) for Time Series Lab.

Fits a full structural time series model using statsmodels UnobservedComponents,
combining level, trend, seasonal, cycle, and autoregressive components.

This is the most flexible UCM specification, encompassing local level and
local linear trend as special cases.
"""

import numpy as np
from statsmodels.tsa.statespace.structural import UnobservedComponents

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"maxiter": 200, "stochastic_cycle": False, "autoregressive": 0},
    "Balanced": {"maxiter": 500, "stochastic_cycle": True, "autoregressive": 0},
    "Thorough": {"maxiter": 1000, "stochastic_cycle": True, "autoregressive": 2},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a structural time series (UCM) model.

    Parameters (via ctx.params)
    ---------------------------
    level : str, optional
        'local level', 'local linear trend', 'smooth trend',
        'random walk', 'fixed intercept'. Default 'local linear trend'.
    seasonal : int or None, optional
        Seasonal period (e.g. 12 for monthly). None for no seasonality.
    cycle : bool, optional
        Whether to include a stochastic cycle. Preset-dependent.
    cycle_bounds : list[float], optional
        [min_period, max_period] for cycle. Default [2, 12].
    autoregressive : int, optional
        AR order for an autoregressive error component. Preset-dependent.
    horizon : int
        Forecast horizon. Default 10.
    alpha : float
        Confidence level. Default 0.05.

    Series layout
    -------------
    First series -> observed time series.
    Additional series -> exogenous regressors.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Exogenous
        all_series = ctx.get_all_series()
        exog_names = []
        exog_arrays = []
        for sname, svals in all_series[1:]:
            if len(svals) >= n:
                exog_arrays.append(svals[:n])
                exog_names.append(sname)
        for ex in ctx.exog:
            arr = np.array(ex.get("values", []), dtype=np.float64)
            if len(arr) >= n:
                exog_arrays.append(arr[:n])
                exog_names.append(ex.get("name", f"Exog{len(exog_names)+1}"))

        if exog_arrays:
            exog = np.column_stack(exog_arrays)
        else:
            exog = None

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 5:
            warnings.append(f"{nan_count} missing values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
            if exog is not None:
                for col in range(exog.shape[1]):
                    nans_e = np.where(np.isnan(exog[:, col]))[0]
                    valid_e = np.where(~np.isnan(exog[:, col]))[0]
                    if len(nans_e) > 0 and len(valid_e) > 2:
                        exog[nans_e, col] = np.interp(nans_e, valid_e, exog[valid_e, col])
        elif nan_count >= n - 5:
            return make_error_response(ctx, "Too few non-missing values to fit structural model.")
        else:
            filled = values

        if n < 10:
            return make_error_response(
                ctx,
                f"Only {n} observations. Structural time series model needs at least 10.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        level_type = ctx.get_param("level", "local linear trend")
        seasonal_period = ctx.get_param("seasonal", None)
        if seasonal_period is not None:
            seasonal_period = int(seasonal_period)
        include_cycle = ctx.get_param("cycle", cfg["stochastic_cycle"])
        ar_order = int(ctx.get_param("autoregressive", cfg["autoregressive"]))
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        alpha = float(ctx.get_param("alpha", 0.05))
        cycle_bounds = ctx.get_param("cycle_bounds", [2, 12])

        # Validate seasonal
        if seasonal_period is not None and n < 2 * seasonal_period:
            warnings.append(
                f"Series length ({n}) < 2 x seasonal period ({seasonal_period}). "
                "Seasonal component may be poorly estimated."
            )

        # Try to infer seasonal period from frequency if not specified
        if seasonal_period is None:
            freq_map = {"D": 7, "B": 5, "W": 52, "M": 12, "MS": 12, "Q": 4, "QS": 4, "H": 24}
            freq = (ctx.frequency or "").strip().upper()
            if freq in freq_map and n >= 2 * freq_map[freq]:
                seasonal_period = freq_map[freq]
                warnings.append(f"Seasonal period inferred as {seasonal_period} from frequency '{ctx.frequency}'.")

        progress_callback("Fitting structural time series model", 20)

        # Build model specification
        model_kwargs = {
            "level": level_type,
        }
        if seasonal_period is not None:
            model_kwargs["seasonal"] = seasonal_period

        if include_cycle:
            model_kwargs["cycle"] = True
            model_kwargs["stochastic_cycle"] = True
            if cycle_bounds:
                model_kwargs["damped_cycle"] = True

        if ar_order > 0:
            model_kwargs["autoregressive"] = ar_order

        try:
            model = UnobservedComponents(filled, exog=exog, **model_kwargs)
            fit = model.fit(maxiter=cfg["maxiter"], disp=False)
        except Exception as e1:
            # Fallback: simplify
            warnings.append(f"Full model failed ({e1}). Trying simplified specification.")
            model_kwargs = {"level": level_type}
            if seasonal_period is not None and n >= 2 * seasonal_period:
                model_kwargs["seasonal"] = seasonal_period
            model = UnobservedComponents(filled, exog=exog, **model_kwargs)
            fit = model.fit(maxiter=cfg["maxiter"], disp=False)
            include_cycle = False
            ar_order = 0

        if not fit.mle_retvals.get("converged", True):
            warnings.append("Model did not fully converge. Results may be approximate.")

        progress_callback("Extracting smoothed components", 45)

        # Extract components
        components = {}
        component_names = []

        level_vals = fit.level.smoothed
        if hasattr(level_vals, 'values'):
            level_vals = level_vals.values
        components["Level"] = level_vals
        component_names.append("Level")

        if hasattr(fit, 'trend') and fit.trend is not None:
            trend_vals = fit.trend.smoothed
            if hasattr(trend_vals, 'values'):
                trend_vals = trend_vals.values
            components["Trend"] = trend_vals
            component_names.append("Trend")

        if seasonal_period is not None and hasattr(fit, 'seasonal') and fit.seasonal is not None:
            seas_vals = fit.seasonal.smoothed
            if hasattr(seas_vals, 'values'):
                seas_vals = seas_vals.values
            components["Seasonal"] = seas_vals
            component_names.append("Seasonal")

        if include_cycle and hasattr(fit, 'cycle') and fit.cycle is not None:
            cycle_vals = fit.cycle.smoothed
            if hasattr(cycle_vals, 'values'):
                cycle_vals = cycle_vals.values
            components["Cycle"] = cycle_vals
            component_names.append("Cycle")

        if ar_order > 0 and hasattr(fit, 'autoregressive') and fit.autoregressive is not None:
            ar_vals = fit.autoregressive.smoothed
            if hasattr(ar_vals, 'values'):
                ar_vals = ar_vals.values
            components["AR"] = ar_vals
            component_names.append("AR")

        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = filled - fitted

        progress_callback("Generating forecasts", 60)

        # Forecast (need future exog if exog was used)
        if exog is not None:
            exog_future = np.tile(exog[-1, :], (horizon, 1))
            warnings.append("Future exogenous values set to last observed values for forecasting.")
        else:
            exog_future = None

        fc_result = fit.get_forecast(steps=horizon, exog=exog_future, alpha=alpha)
        fc_mean = fc_result.predicted_mean
        if hasattr(fc_mean, 'values'):
            fc_mean = fc_mean.values
        fc_mean = np.asarray(fc_mean, dtype=np.float64)

        ci_df = fc_result.conf_int(alpha=alpha)
        if hasattr(ci_df, 'values'):
            ci = ci_df.values
        else:
            ci = np.asarray(ci_df)

        progress_callback("Building output tables", 75)

        ci_pct = int((1 - alpha) * 100)
        tables = []

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc_mean[h]), 6),
                round(float(ci[h, 0]), 6),
                round(float(ci[h, 1]), 6),
            ])
        tables.append(make_table(
            "Forecast",
            ["Step", "Forecast", f"Lower {ci_pct}%", f"Upper {ci_pct}%"],
            fc_rows,
        ))

        # ---- Components table ----
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        cols = ["Time", name] + component_names + ["Fitted", "Residual"]
        comp_rows = []
        for t in range(n):
            row = [time_col[t], round(float(filled[t]), 6)]
            for cname in component_names:
                c_arr = components[cname]
                val = float(c_arr[t]) if t < len(c_arr) and not np.isnan(c_arr[t]) else None
                row.append(round(val, 6) if val is not None else None)
            row.append(round(float(fitted[t]), 6) if not np.isnan(fitted[t]) else None)
            row.append(round(float(residuals[t]), 6) if not np.isnan(residuals[t]) else None)
            comp_rows.append(row)
        tables.append(make_table("Smoothed Components", cols, comp_rows))

        # ---- Parameters table ----
        params = fit.params
        param_names_list = params.index.tolist() if hasattr(params, 'index') else [f"p{i}" for i in range(len(params))]
        pvalues = fit.pvalues
        bse = fit.bse
        param_rows = []
        for i, pn in enumerate(param_names_list):
            param_rows.append([
                pn,
                round(float(params.iloc[i] if hasattr(params, 'iloc') else params[i]), 6),
                round(float(bse.iloc[i] if hasattr(bse, 'iloc') else bse[i]), 6),
                round(float(pvalues.iloc[i] if hasattr(pvalues, 'iloc') else pvalues[i]), 6),
            ])
        tables.append(make_table("Model Parameters", ["Parameter", "Estimate", "Std Error", "P-Value"], param_rows))

        # ---- Model summary ----
        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        # Variance decomposition
        var_decomp_rows = []
        total_var = np.var(filled)
        for cname in component_names:
            c_arr = components[cname]
            c_var = np.var(c_arr[~np.isnan(c_arr)]) if np.any(~np.isnan(c_arr)) else 0.0
            pct = c_var / total_var * 100 if total_var > 0 else 0.0
            var_decomp_rows.append([cname, round(c_var, 6), round(pct, 1)])
        if valid_resid.any():
            r_var = np.var(valid_resid)
            var_decomp_rows.append(["Residual", round(float(r_var), 6), round(float(r_var / total_var * 100) if total_var > 0 else 0.0, 1)])
        tables.append(make_table("Variance Decomposition", ["Component", "Variance", "% of Total"], var_decomp_rows))

        summary_rows = [
            ["Model", f"Structural TS ({level_type})"],
            ["Seasonal Period", seasonal_period if seasonal_period else "None"],
            ["Cycle", "Yes" if include_cycle else "No"],
            ["AR Order", ar_order],
            ["Exogenous Variables", ", ".join(exog_names) if exog_names else "None"],
            ["Observations", n],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Forecast Horizon", horizon],
        ]
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Residual diagnostics ----
        progress_callback("Residual diagnostics", 90)
        diag_rows = []
        if len(valid_resid) > 1:
            diag_rows.append(["Residual Mean", round(float(np.mean(valid_resid)), 6)])
            diag_rows.append(["Residual Std", round(float(np.std(valid_resid, ddof=1)), 6)])
        if len(valid_resid) > 10:
            from scipy import stats as sp_stats
            jb, jb_p = sp_stats.jarque_bera(valid_resid)
            diag_rows.append(["Jarque-Bera", round(float(jb), 4)])
            diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
            if jb_p < 0.05:
                warnings.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")
            dw = float(np.sum(np.diff(valid_resid) ** 2) / np.sum(valid_resid ** 2))
            diag_rows.append(["Durbin-Watson", round(dw, 4)])
        tables.append(make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows))

        # ---- Plain English ----
        comp_list = ", ".join(component_names)
        plain = (
            f"Structural time series model ({level_type}) fitted to '{name}' ({n} observations). "
            f"Components: {comp_list}. "
        )
        if seasonal_period:
            seas_arr = components.get("Seasonal")
            if seas_arr is not None:
                seas_amp = float(np.max(seas_arr[~np.isnan(seas_arr)]) - np.min(seas_arr[~np.isnan(seas_arr)]))
                plain += f"Seasonal amplitude: {seas_amp:.4f}. "
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += f"AIC = {fit.aic:.1f}. {horizon}-step forecast produced."

        charting = (
            "Multi-panel chart stacked vertically sharing x-axis: "
            "Original series with fitted overlay and forecast, "
            "plus one panel per component (Level, Trend, Seasonal, Cycle, AR). "
            "Bottom panel: residuals."
        )

        progress_callback("Done", 100)

        audit = {
            "model": f"structural_ts_{level_type}",
            "level_type": level_type,
            "seasonal_period": seasonal_period,
            "cycle": include_cycle,
            "ar_order": ar_order,
            "exogenous": exog_names,
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "log_likelihood": round(float(fit.llf), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "components": component_names,
            "horizon": horizon,
        }

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Structural time series model failed: {e}",
            error_fixes=[
                "Try a simpler level specification (e.g. 'local level').",
                "Remove the cycle component if the series is short.",
                "Ensure the seasonal period is appropriate.",
                "Check for constant or near-constant series.",
            ],
        )
