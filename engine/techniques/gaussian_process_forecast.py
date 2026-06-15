"""
Gaussian Process Forecast for Time Series Lab.

Uses sklearn GaussianProcessRegressor with an RBF + WhiteKernel
to produce probabilistic time series forecasts with uncertainty quantification.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)


_PRESET_CONFIG = {
    "Fast": {"n_restarts": 2, "max_train": 200, "alpha": 1e-5},
    "Balanced": {"n_restarts": 5, "max_train": 500, "alpha": 1e-7},
    "Thorough": {"n_restarts": 15, "max_train": 1000, "alpha": 1e-10},
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


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Gaussian process regression forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    kernel : str, optional
        Kernel type: "rbf" (default), "matern", or "rational_quadratic".
    confidence_level : float
        Confidence level for intervals. Default 0.95.
    normalize : bool
        Whether to z-score normalize before fitting. Default True.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import (
            RBF, WhiteKernel, ConstantKernel, Matern, RationalQuadratic,
        )
        from scipy import stats as sp_stats

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
                "Gaussian process needs at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        # CAI Phase 2 Session 26 fix (F-ML-GP-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=["Use a positive integer for forecast horizon."],
            )
        conf_level = float(ctx.get_param("confidence_level", 0.95))
        # CAI Phase 2 Session 26 fix (F-ML-GP-CONFLEVEL): explicit
        # range gate.
        if not (0.0 < conf_level < 1.0):
            return make_error_response(
                ctx,
                f"confidence_level must be in (0, 1). Got {conf_level}.",
                error_fixes=["Use a value strictly between 0 and 1."],
            )
        alpha_ci = 1.0 - conf_level
        _nm = ctx.get_param("normalize", True)
        normalize = _nm if isinstance(_nm, bool) else str(_nm).strip().lower() in ("true", "1", "yes")
        kernel_type = ctx.get_param("kernel", "rbf").lower()
        # CAI Phase 2 Session 26 fix (F-ML-GP-KERNEL): explicit
        # allowlist gate. Pre-fix, invalid kernel silently fell
        # through to RBF via if/elif/else.
        _KERNEL_OPTS = ("rbf", "matern", "rational_quadratic")
        if kernel_type not in _KERNEL_OPTS:
            return make_error_response(
                ctx,
                f"Unknown kernel '{kernel_type}'. Must be one of: "
                f"{', '.join(_KERNEL_OPTS)}.",
                error_fixes=[
                    "Use 'rbf' (default; squared exponential), "
                    "'matern' (Matern 2.5), or 'rational_quadratic'.",
                ],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_restarts = preset_cfg["n_restarts"]  # Tier 1b-bis: banked (net-new + ~inert)
        max_train = preset_cfg["max_train"]
        # gp_alpha (GP noise floor): wired this unit; blank -> preset alpha
        # (preset-aware, byte-identical). Literal get_param for catalog_key_alignment.
        _ga = ctx.get_param("gp_alpha", preset_cfg["alpha"])
        gp_alpha = preset_cfg["alpha"] if (_ga is None or str(_ga).strip() == "") else float(_ga)
        from techniques._validation import ParamError, require
        try:
            require(gp_alpha > 0, f"gp_alpha ({gp_alpha}) must be > 0.",
                    fixes=["Use a positive noise level (e.g. 1e-7), or leave blank for the preset default."])
        except ParamError as e:
            return make_error_response(ctx, str(e), error_fixes=e.fixes)

        # Subsample if series is too long (GP is O(n^3))
        if n > max_train:
            warn_list.append(
                f"Series length ({n}) exceeds max for GP ({max_train}). "
                f"Using last {max_train} observations."
            )
            clean = clean[-max_train:]
            n = len(clean)

        progress_callback("Preparing data", 15)

        # Normalize
        if normalize:
            y_mean = float(np.mean(clean))
            y_std = float(np.std(clean, ddof=1))
            if y_std == 0:
                y_std = 1.0
            y_norm = (clean - y_mean) / y_std
        else:
            y_mean = 0.0
            y_std = 1.0
            y_norm = clean.copy()

        # Use time index as input
        X_train = np.arange(n).reshape(-1, 1).astype(float)
        X_forecast = np.arange(n, n + horizon).reshape(-1, 1).astype(float)
        X_all = np.vstack([X_train, X_forecast])

        progress_callback("Building kernel", 20)

        # Kernel construction
        length_scale_init = float(n) / 5.0
        if kernel_type == "matern":
            base_kernel = Matern(length_scale=length_scale_init, nu=2.5)
        elif kernel_type == "rational_quadratic":
            base_kernel = RationalQuadratic(length_scale=length_scale_init, alpha=1.0)
        else:
            base_kernel = RBF(length_scale=length_scale_init)

        kernel = (
            ConstantKernel(1.0, (1e-3, 1e3)) *
            base_kernel +
            WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-10, 1e1))
        )

        progress_callback("Fitting Gaussian process", 30)

        gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=gp_alpha,
            n_restarts_optimizer=n_restarts,
            normalize_y=False,
            random_state=ctx.seed,
        )
        gp.fit(X_train, y_norm)

        progress_callback("Generating predictions", 65)

        # Predict on all points (train + forecast)
        y_pred_all, y_std_all = gp.predict(X_all, return_std=True)

        # Denormalize
        y_pred_all = y_pred_all * y_std + y_mean
        y_std_all = y_std_all * y_std

        # Split
        y_pred_train = y_pred_all[:n]
        y_std_train = y_std_all[:n]
        y_pred_fc = y_pred_all[n:]
        y_std_fc = y_std_all[n:]

        # Confidence intervals. The GP posterior std returned by
        # ``gp.predict(return_std=True)`` is a Bayesian credible band for
        # the latent function conditional on the fitted kernel — NOT a
        # frequentist prediction interval. Coverage depends on the kernel
        # capturing the true data-generating autocovariance; when it does
        # not (a common case for macro series), the reported band
        # underestimates real forecast uncertainty. Emit a warning and
        # disclose in the audit sheet so the user knows to bootstrap if
        # empirical coverage matters.
        z = sp_stats.norm.ppf(1.0 - alpha_ci / 2)
        fc_lower = y_pred_fc - z * y_std_fc
        fc_upper = y_pred_fc + z * y_std_fc
        warn_list.append(
            "GP confidence bands are Bayesian credible intervals conditional "
            "on the fitted kernel. They are not guaranteed frequentist "
            "prediction intervals: if the kernel does not capture the true "
            "autocovariance of the series (common on macro data), reported "
            "coverage will be optimistic. For calibrated coverage, use a "
            "rolling-origin bootstrap re-fit or the Conformal Prediction "
            "Intervals technique."
        )

        progress_callback("Building output", 85)

        # Forecast table
        ci_label = f"{conf_level * 100:.0f}%"
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(y_pred_fc[i]), 6),
                round(float(y_std_fc[i]), 6),
                round(float(fc_lower[i]), 6),
                round(float(fc_upper[i]), 6),
            ])
        fc_table = make_table(
            "Forecast",
            ["Step", "Forecast", "Std Dev", f"Lower {ci_label}", f"Upper {ci_label}"],
            fc_rows,
        )

        # Fitted values table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        fitted_rows = []
        for i in range(n):
            fitted_rows.append([
                time_col[i],
                round(float(clean[i]), 6),
                round(float(y_pred_train[i]), 6),
                round(float(clean[i] - y_pred_train[i]), 6),
                round(float(y_std_train[i]), 6),
            ])
        fitted_table = make_table(
            "Fitted Values",
            ["Time", name, "Fitted", "Residual", "Std Dev"],
            fitted_rows,
        )

        # Model diagnostics
        residuals = clean - y_pred_train
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        r2 = float(1.0 - np.sum(residuals ** 2) / np.sum((clean - np.mean(clean)) ** 2))

        # Log marginal likelihood
        lml = float(gp.log_marginal_likelihood_value_)

        # Kernel info
        kernel_str = str(gp.kernel_)

        summary_rows = [
            ["Kernel", kernel_str],
            ["Kernel Type", kernel_type],
            ["Log Marginal Likelihood", round(lml, 4)],
            ["RMSE", round(rmse, 4)],
            ["MAE", round(mae, 4)],
            ["R-squared", round(r2, 4)],
            ["Observations", n],
            ["Horizon", horizon],
            ["Normalized", normalize],
            ["Optimizer Restarts", n_restarts],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Uncertainty analysis
        avg_fc_std = float(np.mean(y_std_fc))
        avg_train_std = float(np.mean(y_std_train))
        uncertainty_growth = avg_fc_std / max(avg_train_std, 1e-10)

        if uncertainty_growth > 5:
            warn_list.append(
                f"Forecast uncertainty grows {uncertainty_growth:.1f}x compared to in-sample. "
                "Forecasts far from training data carry high uncertainty."
            )

        if r2 < 0:
            warn_list.append(
                "Negative R-squared indicates the GP fit is worse than predicting the mean."
            )

        plain_english = (
            f"Gaussian process forecast for '{name}' ({n} observations) with "
            f"{kernel_type.upper()} kernel. "
            f"In-sample: RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"Log marginal likelihood={lml:.2f}. "
            f"{horizon}-step forecast produced with mean forecast std={avg_fc_std:.4f}."
        )

        charting = (
            "Line chart with original series (dots), GP mean prediction (line), "
            f"and shaded {ci_label} confidence band. "
            "The band should widen in the forecast region. "
            "Secondary panel: residual plot."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(y_pred_fc[-1]) if len(y_pred_fc) else _last_observed_value
        # D17 — length-scale-at-bound detection. Try to extract length_scale
        # from the fitted kernel hyperparameters. sklearn exposes
        # theta-log-space and hyperparameter metadata on gp.kernel_.
        _length_scale = None
        _length_scale_lower_bound = 1e-5  # sklearn default
        try:
            for hyp in gp.kernel_.hyperparameters:
                if "length_scale" in hyp.name:
                    _length_scale = float(
                        np.exp(gp.kernel_.theta[list(
                            h.name for h in gp.kernel_.hyperparameters
                        ).index(hyp.name)])
                    )
                    if hasattr(hyp, "bounds") and hyp.bounds is not None:
                        try:
                            _length_scale_lower_bound = float(hyp.bounds[0][0])
                        except Exception:
                            pass
                    break
        except Exception:
            pass

        audit = {
            "kernel_type": kernel_type,
            "kernel_params": kernel_str,
            "gp_alpha": gp_alpha,
            "log_marginal_likelihood": round(lml, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "avg_forecast_std": round(avg_fc_std, 4),
            "horizon": horizon,
            "n_observations": n,
            "normalized": normalize,
            "length_scale": round(_length_scale, 6) if _length_scale is not None else None,
            "length_scale_lower_bound": _length_scale_lower_bound,
            "series_mean": round(_series_mean, 6),
            "series_std": round(_series_std, 6),
            "last_observed_value": round(_last_observed_value, 6),
            "forecast_end_value": round(_forecast_end_value, 6),
            "series_name": name,
            **format_significance_disclosure(
                test_name="GP Bayesian credible interval (kernel-conditional)",
                critical_value_formula=(
                    "mean ± z(1-α/2) · posterior_std from "
                    "sklearn.GaussianProcessRegressor.predict(return_std=True)"
                ),
                ac_corrected=False,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("gaussian_process_forecast", dict(audit))

        return make_response(
            ctx,
            tables=[fc_table, fitted_table, summary_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Gaussian process forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=10).",
                "GP is computationally expensive for large datasets; try Fast preset.",
                "Try normalize=True if data has a large range.",
                "Check that scikit-learn is installed.",
            ],
        )
