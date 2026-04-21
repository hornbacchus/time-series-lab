"""
Local Level Model (Random Walk + Noise) for Time Series Lab.

Fits a local level model using statsmodels UnobservedComponents:
  y(t) = mu(t) + epsilon(t)
  mu(t) = mu(t-1) + eta(t)

Also known as the random walk plus noise model or simple structural
time series model. Estimation via maximum likelihood with the Kalman filter.
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
    "Fast": {"maxiter": 100, "compute_ci": False},
    "Balanced": {"maxiter": 500, "compute_ci": True},
    "Thorough": {"maxiter": 1000, "compute_ci": True},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a local level model.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    alpha : float, optional
        Confidence level for intervals. Default 0.05 (95%).

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

        # Handle NaN: interpolate
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 3:
            warnings.append(f"{nan_count} missing values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
        elif nan_count >= n - 3:
            return make_error_response(ctx, "Too few non-missing values to fit model.")
        else:
            filled = values

        if n < 8:
            return make_error_response(
                ctx,
                f"Only {n} observations. Local level model needs at least 8.",
                error_fixes=["Provide a longer series."],
            )

        horizon = max(1, int(ctx.get_param("horizon", 10)))
        alpha = float(ctx.get_param("alpha", 0.05))
        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Fitting local level model", 20)

        model = UnobservedComponents(filled, level="local level")
        fit = model.fit(maxiter=cfg["maxiter"], disp=False)

        if not fit.mle_retvals.get("converged", True):
            warnings.append("Model did not fully converge. Results may be approximate.")

        progress_callback("Extracting state components", 50)

        # Smoothed level
        level = fit.level.smoothed
        if hasattr(level, 'values'):
            level = level.values

        # Fitted values and residuals
        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = filled - fitted

        progress_callback("Generating forecasts", 65)

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

        progress_callback("Building output tables", 80)

        # ---- Forecast table ----
        ci_pct = int((1 - alpha) * 100)
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

        # ---- Smoothed state table ----
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        state_rows = []
        for t in range(n):
            state_rows.append([
                time_col[t],
                round(float(filled[t]), 6),
                round(float(level[t]) if t < len(level) and not np.isnan(level[t]) else 0.0, 6),
                round(float(fitted[t]) if not np.isnan(fitted[t]) else 0.0, 6),
                round(float(residuals[t]) if not np.isnan(residuals[t]) else 0.0, 6),
            ])
        state_table = make_table(
            "Smoothed Components",
            ["Time", name, "Level", "Fitted", "Residual"],
            state_rows,
        )

        # ---- Model summary ----
        # Extract variance parameters. Prompt C3 fix: statsmodels
        # exposes parameter names via ``fit.param_names`` (a list),
        # not via ``fit.params.index`` (which is only present when
        # ``params`` is a pandas Series; for UnobservedComponents
        # ``fit.params`` is a plain numpy array). Prior code tried
        # ``params.index.tolist()``, fell into the ``[f"param_{i}"]``
        # fallback, and silently failed to match "irregular" / "level"
        # substrings — sigma_obs and sigma_level both returned None.
        params = fit.params
        param_names = list(getattr(fit, "param_names", None) or (
            params.index.tolist() if hasattr(params, "index")
            else [f"param_{i}" for i in range(len(params))]
        ))
        sigma_obs = None
        sigma_level = None
        for i, pn in enumerate(param_names):
            val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
            if 'irregular' in pn.lower() or 'obs' in pn.lower():
                sigma_obs = val
            elif 'level' in pn.lower():
                sigma_level = val

        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        # Signal-to-noise ratio
        q_ratio = sigma_level / sigma_obs if sigma_obs and sigma_level and sigma_obs > 0 else None

        summary_rows = [
            ["Model", "Local Level (Random Walk + Noise)"],
            ["Observations", n],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Forecast Horizon", horizon],
        ]
        if sigma_obs is not None:
            summary_rows.append(["Observation Noise Variance", round(sigma_obs, 6)])
        if sigma_level is not None:
            summary_rows.append(["Level Variance", round(sigma_level, 6)])
        if q_ratio is not None:
            summary_rows.append(["Signal-to-Noise Ratio (q)", round(q_ratio, 4)])
            if q_ratio < 0.01:
                warnings.append(
                    f"Signal-to-noise ratio is very low (q={q_ratio:.4f}), "
                    "suggesting the level changes very slowly (nearly constant mean)."
                )
            elif q_ratio > 10:
                warnings.append(
                    f"Signal-to-noise ratio is high (q={q_ratio:.4f}), "
                    "suggesting the level changes rapidly (close to a random walk)."
                )

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

        # ---- Plain English ----
        plain = (
            f"Local level model fitted to '{name}' ({n} observations). "
            f"The model decomposes the series into a slowly-varying level and observation noise. "
        )
        if q_ratio is not None:
            if q_ratio < 0.1:
                plain += "The level changes slowly, indicating a fairly stable mean. "
            elif q_ratio > 1:
                plain += "The level changes rapidly, adapting quickly to new observations. "
            else:
                plain += f"Signal-to-noise ratio = {q_ratio:.3f}. "
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += f"AIC = {fit.aic:.1f}. {horizon}-step forecast produced."

        charting = (
            "Line chart with original series, smoothed level overlaid, and forecast "
            "continuation with shaded confidence band. "
            "Secondary panel: standardised residuals with +/- 2 bounds."
        )

        progress_callback("Done", 100)

        # Prompt C3: q-band label + naive baseline + trend-extrapolation
        # fields for the local_level interpretation spec.
        def _q_band(q):
            if q is None:
                return None
            qf = float(q)
            if qf < 0.01: return "very low"
            if qf < 0.1:  return "low"
            if qf < 1:    return "moderate"
            if qf < 10:   return "high"
            return "very high"
        q_band_label = _q_band(q_ratio)

        from techniques.base import fit_naive_baseline
        baseline = fit_naive_baseline(
            filled, frequency=ctx.frequency, horizon=horizon, mode="last",
        )
        last_observed_value = float(filled[-1]) if len(filled) > 0 else 0.0
        forecast_end_value = float(np.asarray(fc_mean)[-1]) if len(fc_mean) > 0 else 0.0
        series_mean = float(np.nanmean(filled)) if len(filled) > 0 else 0.0
        series_std = float(np.nanstd(filled, ddof=1)) if len(filled) > 1 else 0.0
        # Extract JB p and final smoothed level for Tier 2 / Tier 3.
        jb_p_out = None
        try:
            from scipy import stats as _sp_stats
            jb_p_out = float(_sp_stats.jarque_bera(valid_resid).pvalue) if len(valid_resid) > 10 else None
        except Exception:
            pass
        smoothed_final_level = float(fit.level.smoothed[-1]) if hasattr(fit, "level") else None

        audit = {
            "model": "local_level",
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "log_likelihood": round(float(fit.llf), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "mae": round(mae, 4) if mae else None,
            "sigma_obs": round(sigma_obs, 6) if sigma_obs else None,
            "sigma_level": round(sigma_level, 6) if sigma_level else None,
            "signal_to_noise": round(q_ratio, 4) if q_ratio else None,
            "q_band_label": q_band_label,
            "horizon": horizon,
            "baseline_rmse": round(float(baseline["rmse"]), 4),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "smoothed_final_level": smoothed_final_level,
            "jarque_bera_pvalue": round(jb_p_out, 6) if jb_p_out is not None else None,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        interp = build_interpretation("local_level", {
            "series_name": name,
            "n_obs": int(n),
            "horizon": int(horizon),
            "sigma_obs": sigma_obs,
            "sigma_level": sigma_level,
            "q_ratio": q_ratio,
            "q_band_label": q_band_label,
            "aic": float(fit.aic),
            "bic": float(fit.bic),
            "log_likelihood": float(fit.llf),
            "fit_rmse": float(rmse) if rmse else None,
            "baseline_rmse": float(baseline["rmse"]),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "smoothed_final_level": smoothed_final_level,
            "series_mean": series_mean,
            "series_std": series_std,
            "jarque_bera_pvalue": jb_p_out,
        })

        return make_response(
            ctx,
            tables=[fc_table, state_table, summary_table, diag_table],
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
            f"Local level model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Provide at least 8 observations.",
                "Check for constant series (zero variance).",
            ],
        )
