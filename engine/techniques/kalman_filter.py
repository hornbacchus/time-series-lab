"""
Kalman filter (direct-access) for Time Series Lab.

Online filtered-state estimation for a linear Gaussian state-space
model. Supports four named templates (local_level, local_linear_trend,
seasonal, ar1) backed by ``statsmodels.UnobservedComponents``, plus a
``custom`` path that accepts user-supplied (Z, T, R, H, Q) matrices
via a zero-free-parameter MLEModel subclass.

The filter produces one-step-ahead state estimates conditioned on
y_{1:t} (online), contrasted with kalman_smoother which produces
retrospective estimates conditioned on y_{1:T} (full-sample).

Use kalman_filter when:
  - Real-time or streaming inference is needed (the filtered state is
    the best estimate at time t using only past+current observations).
  - Early-period state trajectory matters (the filter is the valid
    representation before smoothing folds in later observations).
  - Custom matrices are already estimated elsewhere and you want to
    run inference at those fixed matrices.

See ``_kalman_common.py`` for shared preset config, param resolution,
and the MLEModel subclass used on the custom path.

References
----------
Kalman 1960 (filter recursions); Harvey 1989 *Forecasting, Structural
Time Series Models and the Kalman Filter*; Durbin & Koopman 2012
*Time Series Analysis by State Space Methods* §4 (filtered/smoothed
covariance ordering). Reference parity check: R `KFAS::KFS` +
`dlm::dlmFilter` (Phase 1 audit 2a).

Audit fields (added Phase 4 Session 8 P4-1.2)
---------------------------------------------
- ``filtered_state_cov``: list of (k, k) per-t one-step posterior
  covariance P_{t|t}; consumed by Pattern F structural invariant
  ``kalman_covariance_ordering`` (P-2 §D.1).
- ``predicted_state_cov``: list of (k, k) per-t predictive covariance
  P_{t|t-1} = T·P_{t-1|t-1}·T' + R·Q·R'.
- ``smoothed_state_cov``: list of (k, k) per-t two-sided smoothed
  covariance P_{t|T}. None on filter-only path; populated when the
  smoother runs.

The structural invariant verifies P_{t|t-1} ≥ P_{t|t} ≥ P_{t|T}
(PSD ordering on the diagonal); see P-2 §D.1 for the checker.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    fit_naive_baseline,
    build_forecast_time_axis as _build_forecast_time_axis,
)
from techniques._kalman_common import (
    _PRESET_CONFIG,
    _resolve_params,
    _build_template_model,
    _build_custom_model,
    _fit_and_smooth,
    _extract_state_table,
    _final_state_summary,
    _template_state_labels,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a linear Gaussian state-space model and emit filtered states.

    Parameters (via ctx.params)
    ---------------------------
    state_space_model : str, default "local_level"
        One of {"local_level", "local_linear_trend", "seasonal",
        "ar1", "custom"}.
    seasonal_period : int, default 12
        Period for the "seasonal" template.
    ar_order : int, default 1
        Order for the "ar1" template (fixed at 1 in this follow-up).
    initialization : str, default "diffuse"
        One of {"diffuse", "known", "approximate_diffuse"}.
    initial_state : list[float], optional
        1D array of length state_dim. Required on "custom" and on
        "known" initialization.
    initial_covariance : list[list[float]], optional
        2D array of shape (state_dim, state_dim). Required on
        "custom" and on "known" initialization.
    observation_matrix_Z : list[list[float]], optional
        Required on "custom". Shape (obs_dim, state_dim).
    transition_matrix_T : list[list[float]], optional
        Required on "custom". Shape (state_dim, state_dim).
    state_intercept_R : list[list[float]], optional
        Optional on "custom". Defaults to identity.
        Shape (state_dim, state_shock_dim).
    observation_noise_H : list[list[float]], optional
        Required on "custom". Shape (obs_dim, obs_dim).
    process_noise_Q : list[list[float]], optional
        Required on "custom". Shape (state_shock_dim, state_shock_dim).
    horizon : int, optional
        Forecast horizon. Preset default.
    alpha : float, default 0.10
        Confidence level for intervals (90% by default).

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

        # Handle NaN: linear interpolation
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 3:
            warnings.append(
                f"{nan_count} missing values linearly interpolated."
            )
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
        elif nan_count >= n - 3:
            return make_error_response(
                ctx, "Too few non-missing values to fit Kalman filter."
            )
        else:
            filled = values

        if n < 8:
            return make_error_response(
                ctx,
                f"Only {n} observations. Kalman filter needs at least 8.",
                error_fixes=["Provide a longer series."],
            )

        # Resolve parameters (raises ValueError on bad template or
        # missing custom matrices)
        try:
            params = _resolve_params(ctx)
        except ValueError as ve:
            return make_error_response(ctx, str(ve))

        template = params["template"]
        horizon = params["horizon"]
        alpha = params["alpha"]

        # --- Build model ---
        progress_callback("Building state-space model", 20)
        try:
            if template == "custom":
                model = _build_custom_model(
                    filled, Z=params["Z"], T=params["T"], R=params["R"],
                    H=params["H"], Q=params["Q"],
                    initial_state=params["initial_state"],
                    initial_covariance=params["initial_covariance"],
                )
                obs_dim = params["Z"].shape[0]
                state_dim = params["T"].shape[0]
                state_labels = [f"state_{i}" for i in range(state_dim)]
            else:
                model = _build_template_model(
                    filled, template,
                    seasonal_period=params["seasonal_period"],
                    ar_order=params["ar_order"],
                )
                obs_dim = 1
                state_labels = _template_state_labels(
                    template, params["seasonal_period"]
                ) or [f"state_{i}" for i in range(
                    getattr(model, "k_states", 1)
                )]
                state_dim = len(state_labels)

            # Validate seasonal period length for template path
            if template == "seasonal":
                if n < 2 * params["seasonal_period"]:
                    warnings.append(
                        f"Series length ({n}) < 2 x seasonal period "
                        f"({params['seasonal_period']}). Seasonal state "
                        "may be poorly estimated."
                    )
        except Exception as e:
            return make_error_response(
                ctx,
                f"Failed to build state-space model: {e}",
                error_fixes=[
                    "Check matrix shapes for custom path.",
                    "Use a named template (local_level, local_linear_trend, "
                    "seasonal, ar1) if custom matrices are not required.",
                ],
            )

        # --- Fit and smooth ---
        progress_callback("Running Kalman filter", 40)
        try:
            fit, converged = _fit_and_smooth(
                model, template, params["maxiter"],
                params["initialization"],
                params["initial_state"],
                params["initial_covariance"],
            )
            if not converged:
                warnings.append(
                    "MLE optimizer did not fully converge. Filter "
                    "estimates may be approximate."
                )
        except Exception as e:
            return make_error_response(
                ctx,
                f"Kalman filter fit failed: {e}",
                error_fixes=[
                    "Check for near-constant series (zero variance).",
                    "For custom path, verify that Q and H are positive "
                    "semi-definite.",
                    "Reduce maxiter or switch to a simpler template.",
                ],
            )

        # --- Extract outputs ---
        progress_callback("Extracting filtered state", 65)
        time_col = ctx.time if ctx.time and len(ctx.time) == n \
            else list(range(1, n + 1))

        state_table = _extract_state_table(
            fit, "filter", state_labels, time_col,
        )

        # Final filtered state for Tier 1 rendering
        final_state_mean, final_state_se = _final_state_summary(
            fit, "filter", state_labels,
        )

        # Fitted values (one-step-ahead predictions) and residuals
        fitted = np.asarray(fit.fittedvalues, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate(
                [np.full(n - len(fitted), np.nan), fitted]
            )
        residuals = filled - fitted
        valid_resid = residuals[~np.isnan(residuals)]

        # RMSE / MAE
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) \
            if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) \
            if len(valid_resid) > 0 else None

        # --- Forecast ---
        progress_callback("Generating forecasts", 80)
        try:
            fc_result = fit.get_forecast(steps=horizon)
            fc_mean = np.asarray(fc_result.predicted_mean, dtype=np.float64)
            ci_df = fc_result.conf_int(alpha=alpha)
            ci = ci_df.values if hasattr(ci_df, "values") else np.asarray(ci_df)
        except Exception as e:
            warnings.append(f"Forecast generation failed: {e}")
            fc_mean = np.full(horizon, np.nan)
            ci = np.full((horizon, 2), np.nan)

        # --- Forecast table ---
        ci_pct = int((1 - alpha) * 100)
        last_label = ctx.time[-1] if ctx.time else None
        fc_time_axis = _build_forecast_time_axis(
            last_label, ctx.frequency or "", horizon,
        )
        fc_rows = []
        for h in range(horizon):
            fc_val = fc_mean[h] if h < len(fc_mean) else np.nan
            lo = ci[h, 0] if h < ci.shape[0] else np.nan
            hi = ci[h, 1] if h < ci.shape[0] else np.nan
            fc_rows.append([
                fc_time_axis[h],
                round(float(fc_val), 6) if np.isfinite(fc_val) else None,
                round(float(lo), 6) if np.isfinite(lo) else None,
                round(float(hi), 6) if np.isfinite(hi) else None,
            ])
        fc_table = make_table(
            "Forecast",
            ["Time", "Forecast", f"Lower {ci_pct}%", f"Upper {ci_pct}%"],
            fc_rows,
        )

        # --- Residual diagnostics ---
        progress_callback("Residual diagnostics", 90)
        jb_p = None
        lb10_p = None
        dw = None
        if len(valid_resid) > 10:
            try:
                from scipy import stats as sp_stats
                jb_stat, jb_p_val = sp_stats.jarque_bera(valid_resid)
                jb_p = float(jb_p_val)
            except Exception:
                pass
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox
                if len(valid_resid) >= 11:
                    _lb = acorr_ljungbox(valid_resid, lags=[10], return_df=True)
                    lb10_p = float(_lb["lb_pvalue"].values[0])
            except Exception:
                pass
            try:
                if np.sum(valid_resid ** 2) > 0:
                    dw = float(
                        np.sum(np.diff(valid_resid) ** 2)
                        / np.sum(valid_resid ** 2)
                    )
            except Exception:
                pass

        diag_rows = []
        if len(valid_resid) > 0:
            diag_rows.append(
                ["Residual Mean", round(float(np.mean(valid_resid)), 6)]
            )
        if len(valid_resid) > 1:
            diag_rows.append(
                ["Residual Std",
                 round(float(np.std(valid_resid, ddof=1)), 6)]
            )
        if jb_p is not None:
            diag_rows.append(["Jarque-Bera P-Value", round(jb_p, 6)])
            if jb_p < 0.05:
                warnings.append(
                    "Residuals may not be normally distributed "
                    "(Jarque-Bera p < 0.05)."
                )
        if lb10_p is not None:
            diag_rows.append(["Ljung-Box Lag-10 P-Value", round(lb10_p, 6)])
            if lb10_p < 0.05:
                warnings.append(
                    "Residuals show autocorrelation at lag 10 "
                    "(Ljung-Box p < 0.05). Model may be misspecified."
                )
        if dw is not None:
            diag_rows.append(["Durbin-Watson", round(dw, 4)])
        if rmse is not None:
            diag_rows.append(["RMSE", round(rmse, 6)])
        if mae is not None:
            diag_rows.append(["MAE", round(mae, 6)])
        diag_table = make_table(
            "Residual Diagnostics", ["Metric", "Value"], diag_rows,
        )

        # --- Baseline comparison ---
        baseline = fit_naive_baseline(
            filled, frequency=ctx.frequency,
            horizon=horizon, mode="last",
        )
        last_observed_value = float(filled[-1]) if len(filled) > 0 else 0.0
        forecast_end_value = float(fc_mean[-1]) \
            if len(fc_mean) > 0 and np.isfinite(fc_mean[-1]) else 0.0
        series_mean = float(np.nanmean(filled)) if len(filled) > 0 else 0.0
        series_std = float(np.nanstd(filled, ddof=1)) \
            if len(filled) > 1 else 0.0

        # --- Log-likelihood / AIC / BIC ---
        try:
            llf = float(fit.llf)
            aic_val = float(fit.aic)
            bic_val = float(fit.bic)
        except Exception:
            llf = None
            aic_val = None
            bic_val = None

        # Custom path: n_free_params = 0 (MLE is a no-op)
        if template == "custom":
            n_free_params = 0
        else:
            try:
                n_free_params = len(fit.params)
            except Exception:
                n_free_params = None

        # --- Signal-to-noise (template_level/local_linear_trend only) ---
        sigma_obs = None
        sigma_level = None
        sigma_slope = None
        q_ratio = None
        if template in ("local_level", "local_linear_trend", "seasonal", "ar1"):
            try:
                pn_list = list(
                    getattr(fit, "param_names", None)
                    or fit.params.index.tolist()
                    if hasattr(fit.params, "index")
                    else [f"param_{i}" for i in range(len(fit.params))]
                )
                for i, pn in enumerate(pn_list):
                    val = float(
                        fit.params.iloc[i]
                        if hasattr(fit.params, "iloc")
                        else fit.params[i]
                    )
                    pn_lower = pn.lower()
                    if "irregular" in pn_lower or "obs" in pn_lower:
                        sigma_obs = val
                    elif "level" in pn_lower and "slope" not in pn_lower:
                        sigma_level = val
                    elif "trend" in pn_lower or "slope" in pn_lower:
                        sigma_slope = val
                if sigma_obs is not None and sigma_obs > 0 \
                        and sigma_level is not None:
                    q_ratio = sigma_level / sigma_obs
            except Exception:
                pass

        # --- Model summary table ---
        summary_rows = [
            ["Wrapper", "Kalman Filter (online)"],
            ["State-Space Model", template],
            ["State Dimension", state_dim],
            ["Observation Dimension", obs_dim],
            ["Observations", n],
            ["Initialization", params["initialization"]],
            ["Forecast Horizon", horizon],
        ]
        if template == "seasonal":
            summary_rows.append(
                ["Seasonal Period", params["seasonal_period"]]
            )
        if template == "ar1":
            summary_rows.append(["AR Order", params["ar_order"]])
        if llf is not None:
            summary_rows.append(["Log-Likelihood", round(llf, 2)])
        if aic_val is not None:
            summary_rows.append(["AIC", round(aic_val, 2)])
        if bic_val is not None:
            summary_rows.append(["BIC", round(bic_val, 2)])
        if n_free_params is not None:
            summary_rows.append(["Free Parameters", n_free_params])
        if rmse is not None:
            summary_rows.append(["RMSE", round(rmse, 4)])
        if sigma_obs is not None:
            summary_rows.append(
                ["Observation Noise Variance", round(sigma_obs, 6)]
            )
        if sigma_level is not None:
            summary_rows.append(["Level Variance", round(sigma_level, 6)])
        if sigma_slope is not None:
            summary_rows.append(["Slope Variance", round(sigma_slope, 6)])
        if q_ratio is not None:
            summary_rows.append(
                ["Signal-to-Noise Ratio (q)", round(q_ratio, 4)]
            )
        summary_table = make_table(
            "Model Summary", ["Metric", "Value"], summary_rows,
        )

        # --- Plain English ---
        plain = (
            f"Kalman filter fitted to '{name}' ({n} observations) "
            f"under the {template} state-space model "
            f"({state_dim}-dim state). "
        )
        if template == "custom":
            plain += (
                f"Custom path: filtered at user-supplied matrices "
                f"with known initialization. "
            )
        else:
            plain += (
                f"MLE-estimated variance components; "
                f"{params['initialization']} initialization. "
            )
        if rmse is not None:
            plain += f"One-step-ahead RMSE = {rmse:.4f}. "
        plain += f"{horizon}-step forecast produced."

        charting = (
            "Line chart: original series, filtered state overlaid, "
            "forecast continuation with shaded confidence band. "
            "Secondary panel: filtered-state trajectory for the "
            "dominant state dimension. Tertiary panel: standardized "
            "residuals with +/- 2 bounds."
        )

        progress_callback("Done", 100)

        # --- Custom-path matrix shape summary (audit only) ---
        custom_matrix_shapes = None
        if template == "custom":
            custom_matrix_shapes = {
                "Z": list(params["Z"].shape),
                "T": list(params["T"].shape),
                "R": list(params["R"].shape) if params["R"] is not None
                     else [state_dim, params["Q"].shape[0]],
                "H": list(params["H"].shape),
                "Q": list(params["Q"].shape),
                "initial_state": list(params["initial_state"].shape),
                "initial_covariance": list(
                    params["initial_covariance"].shape
                ),
            }

        # --- Audit fields ---
        audit = {
            "model": "kalman_filter",
            "state_space_model": template,
            "state_dim": state_dim,
            "obs_dim": obs_dim,
            "state_labels": state_labels,
            "initialization": params["initialization"],
            "log_likelihood": round(llf, 2) if llf is not None else None,
            "aic": round(aic_val, 2) if aic_val is not None else None,
            "bic": round(bic_val, 2) if bic_val is not None else None,
            "n_obs": n,
            "n_effective": n,
            "n_free_params": n_free_params,
            "horizon": horizon,
            "rmse": round(rmse, 4) if rmse is not None else None,
            "mae": round(mae, 4) if mae is not None else None,
            "baseline_rmse": round(float(baseline["rmse"]), 4),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "jarque_bera_pvalue": round(jb_p, 6) if jb_p is not None else None,
            "ljung_box_lag10_pvalue": round(lb10_p, 6) if lb10_p is not None else None,
            "durbin_watson": round(dw, 4) if dw is not None else None,
            "converged": converged,
            "filter_final_state": final_state_mean,
            "filter_final_state_se": final_state_se,
            "sigma_obs": round(sigma_obs, 6) if sigma_obs is not None else None,
            "sigma_level": round(sigma_level, 6) if sigma_level is not None else None,
            "sigma_slope": round(sigma_slope, 6) if sigma_slope is not None else None,
            "signal_to_noise": round(q_ratio, 4) if q_ratio is not None else None,
            "seasonal_period": params["seasonal_period"] if template == "seasonal" else None,
            "ar_order": params["ar_order"] if template == "ar1" else None,
            "custom_matrix_shapes": custom_matrix_shapes,
        }

        # Phase 4 Session 8 (P4-1.2, 2026-05-02) — Kalman covariance
        # ordering invariant precondition (consumed by
        # tools/reference_parity/harness/structural_invariants.py
        # `kalman_covariance_ordering` checker, populated at Phase 3
        # Session 9 + carried into Phase 4 S7 registry expansion).
        # Surfaces the per-time-step covariance arrays from
        # statsmodels' MLEResults so audit-time invariant checking
        # can verify the Kalman filter's recursive covariance
        # contraction property (P_{t|t-1} >= P_{t|t} >= P_{t|T}).
        # Wrapped in try/except so any statsmodels API drift
        # downgrades gracefully — the new audit fields default to
        # None rather than failing the whole run.
        try:
            import numpy as _np_p4s8
            _filt_cov = getattr(fit, "filtered_state_cov", None)
            _pred_cov = getattr(fit, "predicted_state_cov", None)
            _smooth_cov = getattr(fit, "smoothed_state_cov", None)
            audit["filtered_state_cov"] = (
                _np_p4s8.asarray(_filt_cov, dtype=float).tolist()
                if _filt_cov is not None else None
            )
            audit["predicted_state_cov"] = (
                _np_p4s8.asarray(_pred_cov, dtype=float).tolist()
                if _pred_cov is not None else None
            )
            audit["smoothed_state_cov"] = (
                _np_p4s8.asarray(_smooth_cov, dtype=float).tolist()
                if _smooth_cov is not None else None
            )
        except Exception:
            # Defensive: if statsmodels API changes the attribute
            # names or any conversion fails, default to None for
            # all three new fields so the wrapper still produces
            # a valid response.
            audit["filtered_state_cov"] = None
            audit["predicted_state_cov"] = None
            audit["smoothed_state_cov"] = None

        # --- Interpretation ---
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        interp = build_interpretation("kalman_filter", {
            "series_name": name,
            "n_obs": int(n),
            "horizon": int(horizon),
            "state_space_model": template,
            "state_dim": int(state_dim),
            "obs_dim": int(obs_dim),
            "state_labels": list(state_labels),
            "initialization": params["initialization"],
            "filter_final_state": final_state_mean,
            "filter_final_state_se": final_state_se,
            "log_likelihood": llf,
            "aic": aic_val,
            "bic": bic_val,
            "n_free_params": n_free_params,
            "fit_rmse": float(rmse) if rmse is not None else None,
            "baseline_rmse": float(baseline["rmse"]),
            "baseline_label": baseline["label"],
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "series_mean": series_mean,
            "series_std": series_std,
            "jarque_bera_pvalue": jb_p,
            "ljung_box_lag10_pvalue": lb10_p,
            "durbin_watson": dw,
            "converged": converged,
            "sigma_obs": sigma_obs,
            "sigma_level": sigma_level,
            "sigma_slope": sigma_slope,
            "q_ratio": q_ratio,
            "seasonal_period": params["seasonal_period"] if template == "seasonal" else None,
            "ar_order": params["ar_order"] if template == "ar1" else None,
            "custom_matrix_shapes": custom_matrix_shapes,
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
            f"Kalman filter failed: {e}",
            error_fixes=[
                "Ensure the series is numeric and has at least 8 observations.",
                "For custom path, verify all required matrices are supplied "
                "and shapes are consistent.",
                "Try a template path (local_level, local_linear_trend, "
                "seasonal, ar1) if custom setup is uncertain.",
            ],
        )
