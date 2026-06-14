"""
ARIMAX / SARIMAX forecasting with exogenous variables for Time Series Lab.

Fits a SARIMAX model (Seasonal ARIMA with eXogenous regressors) using
statsmodels. Supports both user-specified orders and automatic selection
via information criteria grid search.
"""

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
    format_significance_disclosure,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {
        "max_p": 2, "max_q": 2, "max_d": 1,
        "max_P": 1, "max_Q": 1, "max_D": 1,
        "search": False,
    },
    "Balanced": {
        "max_p": 3, "max_q": 3, "max_d": 2,
        "max_P": 1, "max_Q": 1, "max_D": 1,
        "search": True,
    },
    "Thorough": {
        "max_p": 5, "max_q": 5, "max_d": 2,
        "max_P": 2, "max_Q": 2, "max_D": 1,
        "search": True,
    },
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a SARIMAX model with exogenous regressors.

    Parameters (via ctx.params)
    ---------------------------
    order : list[int], optional
        [p, d, q]. If omitted the Balanced/Thorough presets will search.
    seasonal_order : list[int], optional
        [P, D, Q, m]. Default [0,0,0,0].
    horizon : int
        Forecast steps ahead. Default 10.
    trend : str
        'n', 'c', 't', 'ct'. Default 'c'.
    enforce_stationarity : bool
        Default True.
    enforce_invertibility : bool
        Default True.

    Series layout
    -------------
    First series  -> endogenous (Y).
    Remaining series + ctx.exog -> exogenous regressors (X).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []

        # ---- endogenous ----
        name, y = ctx.get_primary_series()
        n = len(y)

        # ---- exogenous ----
        exog_arrays = []
        exog_names = []
        all_series = ctx.get_all_series()
        for sname, svals in all_series[1:]:
            exog_arrays.append(svals)
            exog_names.append(sname)
        for ex in (ctx.exog or []):
            arr = np.array(ex.get("values", []), dtype=np.float64)
            exog_arrays.append(arr)
            exog_names.append(ex.get("name", f"Exog{len(exog_names)+1}"))

        if not exog_arrays:
            warnings.append(
                "No exogenous variables provided. This is equivalent to plain SARIMA. "
                "Add additional series for ARIMAX/SARIMAX."
            )
            exog = None
        else:
            # Align lengths
            min_len = min(n, *(len(a) for a in exog_arrays))
            if min_len < n:
                warnings.append(
                    f"Exogenous series trimmed to shortest length ({min_len}). "
                    "Ensure all series cover the same time range."
                )
                y = y[:min_len]
                n = min_len
            exog = np.column_stack([a[:n] for a in exog_arrays])

        # ---- NaN handling ----
        if exog is not None:
            mask = ~np.isnan(y)
            for col in range(exog.shape[1]):
                mask &= ~np.isnan(exog[:, col])
            n_dropped = int((~mask).sum())
            if n_dropped > 0:
                warnings.append(f"{n_dropped} rows dropped due to NaN in endogenous or exogenous variables.")
                y = y[mask]
                exog = exog[mask]
                n = len(y)
        else:
            nan_mask = np.isnan(y)
            if nan_mask.any():
                # interpolate interior NaN
                nans = np.where(nan_mask)[0]
                valid = np.where(~nan_mask)[0]
                if len(valid) < 4:
                    return make_error_response(ctx, "Too few non-missing values to fit SARIMAX.")
                y_filled = y.copy()
                y_filled[nans] = np.interp(nans, valid, y[valid])
                y = y_filled
                warnings.append(f"{len(nans)} interior NaN values linearly interpolated.")

        if n < 10:
            return make_error_response(
                ctx,
                f"Only {n} usable observations. SARIMAX requires at least 10.",
                error_fixes=["Provide a longer time series or fewer missing values."],
            )

        # ---- Parameters ----
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        trend = ctx.get_param("trend", "c")
        enforce_stat = ctx.get_param("enforce_stationarity", True)
        enforce_inv = ctx.get_param("enforce_invertibility", True)

        order_param = ctx.get_param("order")
        # The dialog's `order` default is the STRING "auto" -- a SENTINEL for
        # automatic order selection (== unset -> the preset search below). An
        # explicit string parses as comma/space-separated ints ("1,1,1" ->
        # (1,1,1)). Pre-fix BOTH dialog paths were dead: "auto" crashed
        # int('a') and "1,1,1" crashed int(',') -- the tuple(int(x) for x in
        # order_param) cast iterated the raw string char-by-char.
        if isinstance(order_param, str):
            _op = order_param.strip().lower()
            if _op in ("", "auto", "none"):
                order_param = None
            else:
                try:
                    order_param = [int(tok) for tok in _op.replace(";", ",").replace(" ", ",").split(",") if tok.strip()]
                except ValueError:
                    return make_error_response(
                        ctx,
                        f"order must be 'auto' or comma-separated integers "
                        f"(e.g. '1,1,1'), got '{order_param}'.",
                        error_fixes=["Use 'auto' (automatic selection) or p,d,q integers."],
                    )
        seasonal_param = ctx.get_param("seasonal_order", [0, 0, 0, 0])
        seasonal_order = tuple(int(x) for x in seasonal_param) if seasonal_param else (0, 0, 0, 0)

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        if order_param is not None:
            order = tuple(int(x) for x in order_param)
            progress_callback("Fitting SARIMAX with specified order", 20)
            fit = _fit_model(y, exog, order, seasonal_order, trend, enforce_stat, enforce_inv)
        elif cfg["search"]:
            progress_callback("Searching for best SARIMAX order (grid search)", 15)
            order, seasonal_order, fit = _grid_search(
                y, exog, seasonal_order, trend, enforce_stat, enforce_inv, cfg, progress_callback
            )
        else:
            # Fast preset default
            order = (1, 1, 1)
            progress_callback("Fitting SARIMAX(1,1,1)", 20)
            fit = _fit_model(y, exog, order, seasonal_order, trend, enforce_stat, enforce_inv)

        progress_callback("Generating forecasts", 70)

        # ---- Forecasts ----
        if exog is not None and horizon > 0:
            # Need future exogenous values: use last-value carry-forward
            exog_future = np.tile(exog[-1, :], (horizon, 1))
            warnings.append(
                "Future exogenous values not provided; last observed values carried forward for forecasting."
            )
        else:
            exog_future = None

        fc_result = fit.get_forecast(steps=horizon, exog=exog_future)
        fc = fc_result.predicted_mean.values if hasattr(fc_result.predicted_mean, 'values') else np.asarray(fc_result.predicted_mean)
        ci_df = fc_result.conf_int()
        if hasattr(ci_df, 'values'):
            conf_int = ci_df.values
        else:
            conf_int = np.asarray(ci_df)

        # ---- In-sample ----
        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = y - fitted

        # ---- Tables ----
        progress_callback("Building output tables", 80)

        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc[i]), 6),
                round(float(conf_int[i, 0]), 6),
                round(float(conf_int[i, 1]), 6),
            ])
        forecast_table = make_table("Forecast", ["Step", "Forecast", "Lower 95%", "Upper 95%"], fc_rows)

        # Model summary
        order_str = f"({order[0]},{order[1]},{order[2]})"
        seas_str = f"({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]},{seasonal_order[3]})"
        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        summary_rows = [
            ["Order (p,d,q)", order_str],
            ["Seasonal Order (P,D,Q,m)", seas_str],
            ["Exogenous Variables", ", ".join(exog_names) if exog_names else "None"],
            ["Trend", trend],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["HQIC", round(float(fit.hqic), 2)],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Observations", n],
            ["Forecast Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Coefficients table
        coef_rows = []
        params = fit.params
        pvalues = fit.pvalues
        bse = fit.bse
        param_names = params.index.tolist() if hasattr(params, 'index') else [f"param_{i}" for i in range(len(params))]
        for i, pname in enumerate(param_names):
            coef_rows.append([
                pname,
                round(float(params.iloc[i] if hasattr(params, 'iloc') else params[i]), 6),
                round(float(bse.iloc[i] if hasattr(bse, 'iloc') else bse[i]), 6),
                round(float(pvalues.iloc[i] if hasattr(pvalues, 'iloc') else pvalues[i]), 6),
            ])
        coef_table = make_table("Coefficients", ["Parameter", "Estimate", "Std Error", "P-Value"], coef_rows)

        # Residual diagnostics
        progress_callback("Residual diagnostics", 90)
        diag_rows = []
        if len(valid_resid) > 1:
            diag_rows.append(["Residual Mean", round(float(np.mean(valid_resid)), 6)])
            diag_rows.append(["Residual Std", round(float(np.std(valid_resid, ddof=1)), 6)])
        if len(valid_resid) > 10:
            from scipy import stats as sp_stats
            jb, jb_p = sp_stats.jarque_bera(valid_resid)
            diag_rows.append(["Jarque-Bera Statistic", round(float(jb), 4)])
            diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
            if jb_p < 0.05:
                warnings.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")
        diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

        # ---- Plain English ----
        plain = f"SARIMAX{order_str} model fitted to '{name}' ({n} observations)."
        if seasonal_order != (0, 0, 0, 0):
            plain += f" Seasonal component: {seas_str}."
        if exog_names:
            plain += f" Exogenous regressors: {', '.join(exog_names)}."
        if rmse:
            plain += f" RMSE={rmse:.4f}, AIC={fit.aic:.1f}."
        plain += f" {horizon}-step forecast produced."

        charting = (
            "Line chart with original series, fitted values overlaid, and forecast "
            "continuation with shaded 95% confidence band. "
            "Secondary panel: residual plot. "
            "If exogenous variables present, show them on a separate axis."
        )

        progress_callback("Done", 100)

        # Prompt C5 additions: naive baseline, horizon-trend fields,
        # Ljung-Box residual diagnostic, convergence flag, coefficient
        # significance summary.
        from techniques.base import fit_naive_baseline
        baseline = fit_naive_baseline(
            y, frequency=ctx.frequency, horizon=horizon, mode="auto",
        )
        last_observed_value = float(y[-1]) if len(y) > 0 else 0.0
        forecast_end_value = float(np.asarray(fc)[-1]) if len(fc) > 0 else 0.0
        series_mean = float(np.nanmean(y)) if len(y) > 0 else 0.0
        series_std = float(np.nanstd(y, ddof=1)) if len(y) > 1 else 0.0
        lb10_p = None
        jb_p_out = None
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox
            if len(valid_resid) >= 11:
                _lb = acorr_ljungbox(valid_resid, lags=[10], return_df=True)
                lb10_p = float(_lb["lb_pvalue"].values[0])
        except Exception:
            pass
        try:
            from scipy import stats as _sp_stats
            if len(valid_resid) > 10:
                jb_p_out = float(_sp_stats.jarque_bera(valid_resid).pvalue)
        except Exception:
            pass

        # Convergence flag from statsmodels fit
        converged = True
        try:
            converged = bool(fit.mle_retvals.get("converged", True))
        except Exception:
            pass

        # Package exogenous coefficients with p-values for Tier 2
        # disclosure. The SARIMAX params vector is [exog_1, ..., exog_k,
        # AR_1, ..., MA_q, ...]; exog names from user-supplied ctx.exog
        # align with the first ``len(exog_names)`` params when trend is
        # 'c' (the constant) or the first k params when trend='n'.
        # Use fit.params.index (pandas Series) for exact name-to-value
        # matching.
        exog_coef_table = []
        try:
            params_series = fit.params
            params_index = (
                list(params_series.index)
                if hasattr(params_series, "index")
                else [f"p{i}" for i in range(len(params_series))]
            )
            pvalues_series = fit.pvalues
            for i, param_name in enumerate(params_index):
                if param_name in exog_names:
                    est = float(params_series.iloc[i] if hasattr(params_series, "iloc") else params_series[i])
                    p = float(pvalues_series.iloc[i] if hasattr(pvalues_series, "iloc") else pvalues_series[i])
                    exog_coef_table.append({"name": param_name, "estimate": est, "p_value": p})
        except Exception:
            pass

        audit = {
            "order": order_str,
            "seasonal_order": seas_str,
            "exogenous_count": len(exog_names),
            "exogenous_names": exog_names,
            "trend": trend,
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "mae": round(mae, 4) if mae else None,
            "horizon": horizon,
            "baseline_rmse": round(float(baseline["rmse"]), 4),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "ljung_box_lag10_pvalue": round(lb10_p, 6) if lb10_p is not None else None,
            "jarque_bera_pvalue": round(jb_p_out, 6) if jb_p_out is not None else None,
            "converged": converged,
            **format_significance_disclosure(
                test_name="SARIMAX MLE t-tests + Ljung-Box residual diagnostic",
                critical_value_formula=(
                    "statsmodels SARIMAX standard errors via Kalman filter "
                    "MLE; two-sided t-tests at α; Ljung-Box via "
                    "statsmodels.stats.diagnostic.acorr_ljungbox"
                ),
                ac_corrected=True,
            ),
        }

        # Prompt C5 interpretation layer wire-in.
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        _interp_dict = {
            "series_name": name,
            "n_obs": int(n),
            "horizon": int(horizon),
            "order": list(order),
            "seasonal_order": list(seasonal_order),
            "trend": trend,
            "exog_names": list(exog_names),
            "exog_coefs": exog_coef_table,
            "aic": float(fit.aic),
            "bic": float(fit.bic),
            "fit_rmse": float(rmse) if rmse is not None else None,
            "baseline_rmse": float(baseline["rmse"]),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "series_mean": series_mean,
            "series_std": series_std,
            "ljung_box_lag10_pvalue": lb10_p,
            "jarque_bera_pvalue": jb_p_out,
            "converged": converged,
        }
        # Route to arimax vs sarimax spec by technique_id.
        _tid = str(ctx.technique_id or "").lower()
        if _tid == "sarimax" or seasonal_order != (0, 0, 0, 0):
            _target_spec = "sarimax"
        else:
            _target_spec = "arimax"
        interp = build_interpretation(_target_spec, _interp_dict)

        return make_response(
            ctx,
            tables=[forecast_table, summary_table, coef_table, diag_table],
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"SARIMAX failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Check for constant series or perfectly collinear exogenous variables.",
                "Try a simpler order (lower p, d, q) if convergence fails.",
                "Set enforce_stationarity=False if the model fails to converge.",
            ],
        )


def _fit_model(y, exog, order, seasonal_order, trend, enforce_stat, enforce_inv):
    """Fit a single SARIMAX model and return the results."""
    model = SARIMAX(
        y,
        exog=exog,
        order=order,
        seasonal_order=seasonal_order,
        trend=trend,
        enforce_stationarity=enforce_stat,
        enforce_invertibility=enforce_inv,
    )
    return model.fit(disp=False, maxiter=500)


def _grid_search(y, exog, seasonal_order, trend, enforce_stat, enforce_inv, cfg, progress_callback):
    """Search over (p, d, q) grid and return best model by AIC."""
    best_aic = np.inf
    best_order = (1, 1, 1)
    best_fit = None

    max_p = cfg["max_p"]
    max_d = cfg["max_d"]
    max_q = cfg["max_q"]

    total = (max_p + 1) * (max_d + 1) * (max_q + 1)
    count = 0

    for p in range(max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue
                count += 1
                pct = 15 + int(50 * count / total)
                progress_callback(f"Trying SARIMAX({p},{d},{q})", pct)
                try:
                    fit = _fit_model(y, exog, (p, d, q), seasonal_order, trend, enforce_stat, enforce_inv)
                    if fit.aic < best_aic:
                        best_aic = fit.aic
                        best_order = (p, d, q)
                        best_fit = fit
                except Exception:
                    continue

    if best_fit is None:
        # Fallback
        best_order = (1, 0, 0)
        best_fit = _fit_model(y, exog, best_order, seasonal_order, trend, enforce_stat, enforce_inv)

    return best_order, seasonal_order, best_fit
