"""
Support Vector Regression (SVR) Forecast for Time Series Lab.

Uses sklearn SVR with RBF kernel and lag features for time series forecasting.
Supports recursive multi-step forecasting with configurable kernel, C, and epsilon.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {
        "kernel": "rbf", "C": 1.0, "epsilon": 0.1, "gamma": "scale",
        "n_lags": 6, "rolling_windows": [3],
    },
    "Balanced": {
        "kernel": "rbf", "C": 10.0, "epsilon": 0.05, "gamma": "scale",
        "n_lags": 12, "rolling_windows": [3, 6, 12],
    },
    "Thorough": {
        "kernel": "rbf", "C": 100.0, "epsilon": 0.01, "gamma": "scale",
        "n_lags": 12, "rolling_windows": [3, 6, 12],
    },
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


def _create_features(series, n_lags, rolling_windows):
    """
    Create lag features and rolling statistics for each time step.

    Returns: X (n_samples x n_features), y (n_samples,), feature_names (list)
    """
    n = len(series)
    max_lookback = max(n_lags, max(rolling_windows) if rolling_windows else 0)

    if n <= max_lookback + 1:
        return None, None, None

    features = []
    feature_names = []

    # Lag features
    for lag in range(1, n_lags + 1):
        feat = np.full(n, np.nan)
        feat[lag:] = series[:-lag]
        features.append(feat)
        feature_names.append(f"lag_{lag}")

    # Rolling mean features
    for w in rolling_windows:
        feat = np.full(n, np.nan)
        for i in range(w, n):
            feat[i] = np.mean(series[i - w:i])
        features.append(feat)
        feature_names.append(f"roll_mean_{w}")

    # Rolling std features
    for w in rolling_windows:
        if w >= 3:
            feat = np.full(n, np.nan)
            for i in range(w, n):
                feat[i] = np.std(series[i - w:i], ddof=1)
            features.append(feat)
            feature_names.append(f"roll_std_{w}")

    # Difference features
    diff1 = np.full(n, np.nan)
    diff1[1:] = np.diff(series)
    features.append(diff1)
    feature_names.append("diff_1")

    # Time index feature (normalized)
    time_idx = np.arange(n, dtype=float) / n
    features.append(time_idx)
    feature_names.append("time_index")

    X = np.column_stack(features)
    y = series.copy()

    # Remove rows with NaN in features
    valid_mask = ~np.any(np.isnan(X), axis=1)
    X = X[valid_mask]
    y = y[valid_mask]

    return X, y, feature_names


def _create_forecast_features(series, horizon, n_lags, rolling_windows):
    """
    Create features for multi-step-ahead forecasting using recursive approach.
    Returns list of feature vectors for each forecast step.
    """
    extended = series.tolist()
    forecast_features = []

    for h in range(horizon):
        n_ext = len(extended)
        feat = []

        # Lags
        for lag in range(1, n_lags + 1):
            if n_ext - lag >= 0:
                feat.append(extended[n_ext - lag])
            else:
                feat.append(0.0)

        # Rolling means
        for w in rolling_windows:
            if n_ext >= w:
                feat.append(np.mean(extended[n_ext - w:n_ext]))
            else:
                feat.append(np.mean(extended))

        # Rolling stds
        for w in rolling_windows:
            if w >= 3 and n_ext >= w:
                feat.append(np.std(extended[n_ext - w:n_ext], ddof=1))
            elif w >= 3:
                feat.append(0.0)

        # Diff
        if n_ext >= 2:
            feat.append(extended[-1] - extended[-2])
        else:
            feat.append(0.0)

        # Time index (extrapolated)
        feat.append((n_ext) / len(series))

        forecast_features.append(np.array(feat))
        extended.append(0.0)

    return forecast_features


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Support Vector Regression forecast with lag features.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    max_lag : int, optional
        Number of lag features. Default from preset.
    kernel : str, optional
        SVR kernel type. Default "rbf".
    C : float, optional
        Regularization parameter. Default 1.0.
    epsilon : float, optional
        Epsilon in epsilon-SVR model. Default 0.1.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        from sklearn.svm import SVR
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import TimeSeriesSplit

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")
        n = len(clean)

        if n < 20:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "SVR forecast needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        # CAI Phase 2 Session 26 fix (F-ML-SVR-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=["Use a positive integer for forecast horizon."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        # Fix B Tier 1b-bis: blank/absent -> preset cfg (byte-identical); literal
        # get_param keeps keys visible to catalog_key_alignment. (lag key stays
        # "max_lag" -- already wired; the n_lags rename is a banked cosmetic pass.)
        _ml = ctx.get_param("max_lag", preset_cfg["n_lags"])
        n_lags = preset_cfg["n_lags"] if (_ml is None or str(_ml).strip() == "") else int(_ml)
        kernel = ctx.get_param("kernel", preset_cfg["kernel"])
        _c = ctx.get_param("C", preset_cfg["C"])
        C = preset_cfg["C"] if (_c is None or str(_c).strip() == "") else float(_c)
        _eps = ctx.get_param("epsilon", preset_cfg["epsilon"])
        epsilon = preset_cfg["epsilon"] if (_eps is None or str(_eps).strip() == "") else float(_eps)
        # gamma: wired this unit (was preset-only "scale"); accepts scale|auto|
        # positive float. blank -> preset gamma (byte-identical).
        _gm = ctx.get_param("gamma", preset_cfg["gamma"])
        rolling_windows = preset_cfg["rolling_windows"]

        from techniques._validation import ParamError, require
        try:
            require(C > 0, f"C ({C}) must be > 0.",
                    fixes=["Use a positive regularization C, or leave blank for the preset default."])
            require(epsilon >= 0, f"epsilon ({epsilon}) must be >= 0.",
                    fixes=["Use epsilon >= 0, or leave blank."])
            if _gm is None or str(_gm).strip() == "":
                gamma = preset_cfg["gamma"]
            else:
                _gms = str(_gm).strip().lower()
                if _gms in ("scale", "auto"):
                    gamma = _gms
                else:
                    try:
                        gamma = float(_gm)
                    except ValueError:
                        raise ParamError(
                            f"gamma must be 'scale', 'auto', or a positive number, got '{_gm}'.",
                            fixes=["Use 'scale' (default), 'auto', or a positive number."])
                    require(gamma > 0, f"gamma ({gamma}) must be > 0 when numeric.",
                            fixes=["Use a positive number, or 'scale'/'auto'."])
        except ParamError as e:
            return make_error_response(ctx, str(e), error_fixes=e.fixes)

        # CAI Phase 2 Session 26 fix (F-ML-SVR-KERNEL): explicit
        # allowlist gate. Pre-fix, invalid kernel was loud-and-
        # coerced to 'rbf' with warning. Per Session 16 protocol
        # (loud-and-coerced is severe because user's intended
        # computation differs from what ran).
        valid_kernels = ("rbf", "linear", "poly", "sigmoid")
        if kernel not in valid_kernels:
            return make_error_response(
                ctx,
                f"Unknown kernel '{kernel}'. Must be one of: "
                f"{', '.join(valid_kernels)}.",
                error_fixes=[
                    "Use 'rbf' (default; radial basis function), "
                    "'linear', 'poly' (polynomial), or 'sigmoid'.",
                ],
            )

        # Cap lags to reasonable size
        n_lags = min(n_lags, n // 3)

        progress_callback("Creating features", 15)

        X, y, feature_names = _create_features(clean, n_lags, rolling_windows)
        if X is None or len(X) < 10:
            return make_error_response(
                ctx,
                "Not enough data points after feature creation. "
                "Try fewer lags or a longer series.",
                error_fixes=["Reduce max_lag.", "Provide more data."],
            )

        # SVR benefits from feature scaling
        progress_callback("Scaling features", 20)
        scaler_X = StandardScaler()
        X_scaled = scaler_X.fit_transform(X)

        scaler_y = StandardScaler()
        y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).ravel()

        progress_callback("Training SVR model", 30)

        model = SVR(
            kernel=kernel,
            C=C,
            epsilon=epsilon,
            gamma=gamma,
        )
        model.fit(X_scaled, y_scaled)

        # In-sample predictions
        y_pred_scaled = model.predict(X_scaled)
        y_pred_train = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
        train_residuals = y - y_pred_train
        train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
        train_mae = float(np.mean(np.abs(train_residuals)))
        ss_res = float(np.sum(train_residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Number of support vectors
        n_sv = model.n_support_ if hasattr(model, "n_support_") else None
        total_sv = int(np.sum(n_sv)) if n_sv is not None else len(model.support_)

        progress_callback("Cross-validation", 55)

        # Time-series cross-validation
        n_splits = min(3, max(2, len(X) // 20))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X_scaled[train_idx], X_scaled[val_idx]
            y_tr, y_val_s = y_scaled[train_idx], y_scaled[val_idx]
            y_val_orig = y[val_idx]

            cv_model = SVR(kernel=kernel, C=C, epsilon=epsilon, gamma=gamma)
            cv_model.fit(X_tr, y_tr)
            pred_s = cv_model.predict(X_val)
            pred = scaler_y.inverse_transform(pred_s.reshape(-1, 1)).ravel()
            cv_rmse = float(np.sqrt(np.mean((y_val_orig - pred) ** 2)))
            cv_scores.append(cv_rmse)

        avg_cv_rmse = float(np.mean(cv_scores))
        std_cv_rmse = float(np.std(cv_scores, ddof=1)) if len(cv_scores) > 1 else 0.0

        progress_callback("Generating forecasts", 75)

        # Multi-step recursive forecast
        fc_features = _create_forecast_features(clean, horizon, n_lags, rolling_windows)
        extended_for_fc = clean.tolist()
        fc_values = []
        for h in range(horizon):
            feat_scaled = scaler_X.transform(fc_features[h].reshape(1, -1))
            pred_scaled = model.predict(feat_scaled)
            pred = float(scaler_y.inverse_transform(pred_scaled.reshape(-1, 1))[0, 0])
            fc_values.append(pred)
            extended_for_fc.append(pred)
            if h + 1 < horizon:
                fc_features[h + 1] = _create_forecast_features(
                    np.array(extended_for_fc), 1, n_lags, rolling_windows
                )[0]

        fc_values = np.array(fc_values)

        progress_callback("Building output", 90)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([n + i + 1, round(float(fc_values[i]), 6)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # Model summary
        summary_rows = [
            ["Algorithm", "Support Vector Regression (sklearn)"],
            ["Kernel", kernel],
            ["C (Regularization)", C],
            ["Epsilon", epsilon],
            ["Gamma", str(gamma)],
            ["n_lags", n_lags],
            ["Rolling Windows", str(rolling_windows)],
            ["Total Features", len(feature_names)],
            ["Training Samples", len(X)],
            ["Support Vectors", total_sv],
            ["SV Ratio", f"{100 * total_sv / len(X):.1f}%"],
            ["Train RMSE", round(train_rmse, 4)],
            ["Train MAE", round(train_mae, 4)],
            ["Train R-squared", round(train_r2, 4)],
            ["CV RMSE (mean)", round(avg_cv_rmse, 4)],
            ["CV RMSE (std)", round(std_cv_rmse, 4)],
            ["CV Folds", n_splits],
            ["Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [fc_table, summary_table]

        if train_r2 < 0:
            warn_list.append(
                "Negative R-squared on training data indicates the model is worse than "
                "predicting the mean. Try different kernel or C/epsilon values."
            )
        if avg_cv_rmse > 2 * train_rmse:
            warn_list.append(
                "CV RMSE is much higher than training RMSE, suggesting overfitting. "
                "Consider reducing C or increasing epsilon."
            )
        if total_sv > 0.8 * len(X):
            warn_list.append(
                f"Most training points are support vectors ({total_sv}/{len(X)}). "
                "The model may be underfitting. Try increasing C or using a different kernel."
            )
        if horizon > n // 2:
            warn_list.append(
                f"Forecast horizon ({horizon}) is large relative to series length ({n}). "
                "Recursive multi-step forecasts degrade with longer horizons."
            )

        plain_english = (
            f"SVR forecast for '{name}' ({n} observations) using {kernel} kernel "
            f"(C={C}, epsilon={epsilon}). "
            f"{total_sv} support vectors used ({100 * total_sv / len(X):.0f}% of training data). "
            f"Train RMSE={train_rmse:.4f}, CV RMSE={avg_cv_rmse:.4f} ({n_splits}-fold). "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and forecast continuation. "
            "Scatter plot of actual vs. fitted values for training data. "
            "Highlight support vectors in a separate panel if feasible."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(fc_values[-1]) if len(fc_values) else _last_observed_value
        _n_train = int(n - n_lags)
        _sv_ratio = float(total_sv) / float(_n_train) if _n_train > 0 else 0.0

        audit = {
            "kernel": kernel,
            "C": C,
            "epsilon": epsilon,
            "gamma": str(gamma),
            "n_lags": n_lags,
            "n_features": len(feature_names),
            "n_support_vectors": total_sv,
            "sv_ratio": round(_sv_ratio, 4),
            "scaling_applied": True,
            "train_rmse": round(train_rmse, 4),
            "train_mae": round(train_mae, 4),
            "train_r2": round(train_r2, 4),
            "cv_rmse": round(avg_cv_rmse, 4),
            "horizon": horizon,
            "series_mean": round(_series_mean, 6),
            "series_std": round(_series_std, 6),
            "last_observed_value": round(_last_observed_value, 6),
            "forecast_end_value": round(_forecast_end_value, 6),
            "n_train": _n_train,
            "n_obs": n,
            "series_name": name,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("svr_forecast", dict(audit))

        return make_response(
            ctx,
            tables=tables,
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
            f"SVR forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try a different kernel (rbf, linear, poly).",
                "Adjust C and epsilon parameters.",
                "Check that scikit-learn is installed.",
            ],
        )
