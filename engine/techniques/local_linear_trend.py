"""
Local Linear Trend Model for Time Series Lab.

Fits a local linear trend model using statsmodels UnobservedComponents:
  y(t) = mu(t) + epsilon(t)         (observation equation)
  mu(t) = mu(t-1) + nu(t-1) + eta(t)  (level equation)
  nu(t) = nu(t-1) + zeta(t)            (slope equation)

The level and slope both evolve stochastically.
Estimation via maximum likelihood with the Kalman filter.
"""

import numpy as np
from statsmodels.tsa.statespace.structural import UnobservedComponents

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"maxiter": 100},
    "Balanced": {"maxiter": 500},
    "Thorough": {"maxiter": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a local linear trend model.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    damped : bool, optional
        If True, constrain the slope variance to be smaller (damped trend).
        Default False.
    alpha : float
        Confidence level for forecast intervals. Default 0.05.

    Series layout
    -------------
    First series -> observed time series.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 5:
            warnings.append(f"{nan_count} missing values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
        elif nan_count >= n - 5:
            return make_error_response(ctx, "Too few non-missing values to fit local linear trend model.")
        else:
            filled = values

        if n < 10:
            return make_error_response(
                ctx,
                f"Only {n} observations. Local linear trend model needs at least 10.",
                error_fixes=["Provide a longer series."],
            )

        horizon = max(1, int(ctx.get_param("horizon", 10)))
        alpha = float(ctx.get_param("alpha", 0.05))
        damped = ctx.get_param("damped", False)
        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Fitting local linear trend model", 20)

        # 'local linear trend' = stochastic level + stochastic trend
        model = UnobservedComponents(
            filled,
            level="local linear trend",
        )
        fit = model.fit(maxiter=cfg["maxiter"], disp=False)

        if not fit.mle_retvals.get("converged", True):
            warnings.append("Model did not fully converge. Results may be approximate.")

        progress_callback("Extracting smoothed components", 45)

        # Smoothed states
        level = fit.level.smoothed
        trend = fit.trend.smoothed
        if hasattr(level, 'values'):
            level = level.values
        if hasattr(trend, 'values'):
            trend = trend.values

        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = filled - fitted

        progress_callback("Generating forecasts", 60)

        fc_result = fit.get_forecast(steps=horizon, alpha=alpha)
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

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc_mean[h]), 6),
                round(float(ci[h, 0]), 6),
                round(float(ci[h, 1]), 6),
            ])
        fc_table = make_table(
            "Forecast",
            ["Step", "Forecast", f"Lower {ci_pct}%", f"Upper {ci_pct}%"],
            fc_rows,
        )

        # ---- Smoothed components table ----
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        comp_rows = []
        for t in range(n):
            comp_rows.append([
                time_col[t],
                round(float(filled[t]), 6),
                round(float(level[t]) if t < len(level) else 0.0, 6),
                round(float(trend[t]) if t < len(trend) else 0.0, 6),
                round(float(fitted[t]) if not np.isnan(fitted[t]) else 0.0, 6),
                round(float(residuals[t]) if not np.isnan(residuals[t]) else 0.0, 6),
            ])
        comp_table = make_table(
            "Smoothed Components",
            ["Time", name, "Level", "Trend (Slope)", "Fitted", "Residual"],
            comp_rows,
        )

        # ---- Model summary ----
        params = fit.params
        param_names = params.index.tolist() if hasattr(params, 'index') else []

        sigma_obs = sigma_level = sigma_trend = None
        for i, pn in enumerate(param_names):
            val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
            pn_lower = pn.lower()
            if 'irregular' in pn_lower or 'obs' in pn_lower:
                sigma_obs = val
            elif 'trend' in pn_lower or 'slope' in pn_lower:
                sigma_trend = val
            elif 'level' in pn_lower:
                sigma_level = val

        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        # Final slope estimate
        final_slope = float(trend[-1]) if len(trend) > 0 else 0.0

        summary_rows = [
            ["Model", "Local Linear Trend"],
            ["Observations", n],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Final Slope", round(final_slope, 6)],
            ["Forecast Horizon", horizon],
        ]
        if sigma_obs is not None:
            summary_rows.append(["Observation Noise Var", round(sigma_obs, 6)])
        if sigma_level is not None:
            summary_rows.append(["Level Variance", round(sigma_level, 6)])
        if sigma_trend is not None:
            summary_rows.append(["Trend (Slope) Variance", round(sigma_trend, 6)])
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

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
        diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

        # ---- Trend direction interpretation ----
        if final_slope > 0:
            trend_dir = "upward"
        elif final_slope < 0:
            trend_dir = "downward"
        else:
            trend_dir = "flat"

        # Slope stability: compare first-half vs second-half average slopes
        half = len(trend) // 2
        if half > 0:
            avg_slope_first = float(np.mean(trend[:half]))
            avg_slope_second = float(np.mean(trend[half:]))
            slope_change = avg_slope_second - avg_slope_first
        else:
            slope_change = 0.0

        # ---- Plain English ----
        plain = (
            f"Local linear trend model fitted to '{name}' ({n} observations). "
            f"The series shows a {trend_dir} trend with final slope = {final_slope:.4f}. "
        )
        if abs(slope_change) > abs(final_slope) * 0.5 and final_slope != 0:
            plain += "The slope has changed substantially over time. "
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += f"AIC = {fit.aic:.1f}. {horizon}-step forecast produced with widening confidence bands."

        charting = (
            "Three-panel chart: (1) Original series with smoothed level overlay and forecast with "
            "widening confidence fan. (2) Smoothed trend/slope over time showing how the growth rate "
            "evolves. (3) Standardised residuals."
        )

        progress_callback("Done", 100)

        audit = {
            "model": "local_linear_trend",
            "damped": damped,
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "log_likelihood": round(float(fit.llf), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "final_slope": round(final_slope, 6),
            "trend_direction": trend_dir,
            "sigma_obs": round(sigma_obs, 6) if sigma_obs else None,
            "sigma_level": round(sigma_level, 6) if sigma_level else None,
            "sigma_trend": round(sigma_trend, 6) if sigma_trend else None,
            "horizon": horizon,
        }

        return make_response(
            ctx,
            tables=[fc_table, comp_table, summary_table, diag_table],
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
            f"Local linear trend model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with at least 10 observations.",
                "Check for constant series (zero variance).",
                "Try the simpler local_level model if this fails.",
            ],
        )
