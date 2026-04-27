"""
Random Forest Forecast for Time Series Lab.

Uses sklearn RandomForestRegressor with automatically generated
lag features, rolling statistics, and time features for time series forecasting.
Same lag feature approach as gradient_boosting_forecast.py.
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
        "n_estimators": 100, "max_depth": 6, "min_samples_leaf": 5,
        "n_lags": 6, "rolling_windows": [3],
    },
    "Balanced": {
        "n_estimators": 200, "max_depth": 10, "min_samples_leaf": 3,
        "n_lags": 12, "rolling_windows": [3, 6, 12],
    },
    "Thorough": {
        "n_estimators": 500, "max_depth": 15, "min_samples_leaf": 2,
        "n_lags": 24, "rolling_windows": [3, 6, 12, 24],
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
        # Placeholder for recursive prediction (will be set later)
        extended.append(0.0)

    return forecast_features


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Random Forest forecast with lag features.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    max_lag : int, optional
        Number of lag features. Default from preset (n_lags).
    n_estimators : int, optional
        Number of trees. Default 200.
    max_depth : int, optional
        Maximum tree depth. Default 10.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        from sklearn.ensemble import RandomForestRegressor
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
                "Random forest forecast needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        # CAI Phase 2 Session 23 fix (F-TR-RF-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=[
                    "Use a positive integer for the forecast horizon "
                    "(typical values 1-24).",
                ],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_lags = int(ctx.get_param("max_lag", preset_cfg["n_lags"]))
        # CAI Phase 2 Session 23 fix (F-TR-RF-NLAGS): explicit
        # range gate.
        if n_lags < 1:
            return make_error_response(
                ctx,
                f"max_lag must be >= 1. Got {n_lags}.",
                error_fixes=[
                    "Use a positive integer for the number of lagged "
                    "features (typical values 4-24).",
                ],
            )
        n_estimators = int(ctx.get_param("n_estimators", preset_cfg["n_estimators"]))
        max_depth = int(ctx.get_param("max_depth", preset_cfg["max_depth"]))
        min_samples_leaf = preset_cfg["min_samples_leaf"]
        rolling_windows = preset_cfg["rolling_windows"]

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

        progress_callback("Training random forest model", 25)

        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=ctx.seed,
            n_jobs=-1,
        )
        model.fit(X, y)

        # In-sample metrics
        y_pred_train = model.predict(X)
        train_residuals = y - y_pred_train
        train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
        train_mae = float(np.mean(np.abs(train_residuals)))
        ss_res = float(np.sum(train_residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        progress_callback("Cross-validation", 55)

        # Time-series cross-validation
        n_splits = min(3, max(2, len(X) // 20))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]
            cv_model = RandomForestRegressor(
                n_estimators=max(50, n_estimators // 2),
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
                random_state=ctx.seed,
                n_jobs=-1,
            )
            cv_model.fit(X_tr, y_tr)
            pred = cv_model.predict(X_val)
            cv_rmse = float(np.sqrt(np.mean((y_val - pred) ** 2)))
            cv_scores.append(cv_rmse)

        avg_cv_rmse = float(np.mean(cv_scores))
        std_cv_rmse = float(np.std(cv_scores, ddof=1)) if len(cv_scores) > 1 else 0.0

        progress_callback("Generating forecasts", 75)

        # Multi-step recursive forecast
        fc_features = _create_forecast_features(clean, horizon, n_lags, rolling_windows)
        extended_for_fc = clean.tolist()
        fc_values = []
        for h in range(horizon):
            pred = float(model.predict(fc_features[h].reshape(1, -1))[0])
            fc_values.append(pred)
            extended_for_fc.append(pred)
            # Update remaining forecast features with the new prediction
            if h + 1 < horizon:
                fc_features[h + 1] = _create_forecast_features(
                    np.array(extended_for_fc), 1, n_lags, rolling_windows
                )[0]

        fc_values = np.array(fc_values)

        progress_callback("Building output", 90)

        # Feature importance
        importances = model.feature_importances_
        feat_imp = sorted(zip(feature_names, importances), key=lambda x: -x[1])

        imp_rows = []
        for fname, imp in feat_imp[:15]:
            imp_rows.append([fname, round(float(imp), 4)])
        imp_table = make_table("Feature Importance", ["Feature", "Importance"], imp_rows)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([n + i + 1, round(float(fc_values[i]), 6)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # Model summary
        summary_rows = [
            ["Algorithm", "Random Forest (sklearn)"],
            ["n_estimators", n_estimators],
            ["max_depth", max_depth],
            ["min_samples_leaf", min_samples_leaf],
            ["n_lags", n_lags],
            ["Rolling Windows", str(rolling_windows)],
            ["Total Features", len(feature_names)],
            ["Training Samples", len(X)],
            ["Train RMSE", round(train_rmse, 4)],
            ["Train MAE", round(train_mae, 4)],
            ["Train R-squared", round(train_r2, 4)],
            ["CV RMSE (mean)", round(avg_cv_rmse, 4)],
            ["CV RMSE (std)", round(std_cv_rmse, 4)],
            ["CV Folds", n_splits],
            ["Horizon", horizon],
            ["OOB Score", round(float(model.oob_score_), 4) if hasattr(model, "oob_score_") and model.oob_score_ else "N/A"],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        if train_r2 < 0:
            warn_list.append(
                "Negative R-squared on training data indicates the model is worse than "
                "predicting the mean. Data may not have learnable patterns."
            )
        if avg_cv_rmse > 2 * train_rmse:
            warn_list.append(
                "CV RMSE is much higher than training RMSE, suggesting overfitting. "
                "Consider reducing max_depth or increasing min_samples_leaf."
            )
        if horizon > n // 2:
            warn_list.append(
                f"Forecast horizon ({horizon}) is large relative to series length ({n}). "
                "Recursive multi-step forecasts degrade with longer horizons."
            )

        top_feature = feat_imp[0][0] if feat_imp else "N/A"
        plain_english = (
            f"Random forest forecast for '{name}' ({n} observations) with "
            f"{n_lags} lag features and {len(feature_names)} total features. "
            f"Train RMSE={train_rmse:.4f}, CV RMSE={avg_cv_rmse:.4f} ({n_splits}-fold). "
            f"Top feature: {top_feature}. {horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and forecast continuation. "
            "Bar chart of top 10 feature importances. "
            "Scatter plot of actual vs. fitted values for training data."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        # Tree cohort inheritance fields (D1).
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(fc_values[-1]) if len(fc_values) else _last_observed_value
        # Top-5 features with importances (D12 top-K convention)
        _top_features = [
            {"name": str(fname), "importance": round(float(imp), 4)}
            for fname, imp in feat_imp[:5]
        ]
        # Training sample count after lag warmup
        _n_train = int(n - n_lags)

        audit = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "n_lags": n_lags,
            "n_features": len(feature_names),
            "train_rmse": round(train_rmse, 4),
            "train_mae": round(train_mae, 4),
            "train_r2": round(train_r2, 4),
            "cv_rmse": round(avg_cv_rmse, 4),
            "horizon": horizon,
            "top_feature": top_feature,
            "top_features": _top_features,
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
        interp = build_interpretation("random_forest_forecast", dict(audit))

        return make_response(
            ctx,
            tables=[fc_table, summary_table, imp_table],
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
            f"Random forest forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer lags or a simpler model (fewer estimators).",
                "Check that scikit-learn is installed.",
            ],
        )
