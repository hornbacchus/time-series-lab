"""
LightGBM Time Series Forecast for Time Series Lab.

Uses the LightGBM library when available, falling back to sklearn
GradientBoostingRegressor. Generates lag features, rolling statistics,
and time features for recursive multi-step forecasting.

LightGBM is often faster than XGBoost for large datasets and supports
native categorical features and histogram-based splits.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _has_lightgbm():
    try:
        import lightgbm as lgb
        return True
    except ImportError:
        return False


_PRESET_CONFIG = {
    "Fast": {
        "n_estimators": 100, "max_depth": 4, "learning_rate": 0.1,
        "n_lags": 6, "rolling_windows": [3],
        "subsample": 1.0, "colsample_bytree": 1.0,
        "num_leaves": 15,
    },
    "Balanced": {
        "n_estimators": 300, "max_depth": 6, "learning_rate": 0.05,
        "n_lags": 12, "rolling_windows": [3, 6, 12],
        "subsample": 0.8, "colsample_bytree": 0.8,
        "num_leaves": 31,
    },
    "Thorough": {
        "n_estimators": 600, "max_depth": 8, "learning_rate": 0.02,
        "n_lags": 24, "rolling_windows": [3, 6, 12, 24],
        "subsample": 0.7, "colsample_bytree": 0.7,
        "num_leaves": 63,
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
    LightGBM time series forecast with lag features.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    max_lag : int, optional
        Number of lag features. Default from preset.
    n_estimators : int, optional
        Number of boosting rounds. Default 300.
    max_depth : int, optional
        Maximum tree depth. Default 6.
    learning_rate : float, optional
        Boosting learning rate. Default 0.05.
    num_leaves : int, optional
        Maximum number of leaves per tree. Default 31.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

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
                "LightGBM forecast needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_lags = int(ctx.get_param("max_lag", preset_cfg["n_lags"]))
        n_estimators = int(ctx.get_param("n_estimators", preset_cfg["n_estimators"]))
        max_depth = int(ctx.get_param("max_depth", preset_cfg["max_depth"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["learning_rate"]))
        num_leaves = int(ctx.get_param("num_leaves", preset_cfg["num_leaves"]))
        subsample = preset_cfg["subsample"]
        colsample_bytree = preset_cfg["colsample_bytree"]
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

        use_lgb = _has_lightgbm()
        backend = "lightgbm" if use_lgb else "sklearn_gbr"

        if not use_lgb:
            warn_list.append(
                "LightGBM library not available. Falling back to sklearn "
                "GradientBoostingRegressor. Install lightgbm for full support."
            )

        if use_lgb:
            import lightgbm as lgb

            progress_callback("Training LightGBM model", 25)

            model = lgb.LGBMRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=lr,
                num_leaves=num_leaves,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                objective="regression",
                random_state=ctx.seed,
                verbosity=-1,
            )
            model.fit(X, y)

            importances = model.feature_importances_.astype(float)
            # Normalize to sum to 1 for comparability
            imp_sum = importances.sum()
            if imp_sum > 0:
                importances = importances / imp_sum
            model_desc = "LightGBM (lightgbm library)"
        else:
            from sklearn.ensemble import GradientBoostingRegressor

            progress_callback("Training sklearn GBR model", 25)

            model = GradientBoostingRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=lr,
                loss="squared_error",
                random_state=ctx.seed,
                subsample=subsample,
            )
            model.fit(X, y)

            importances = model.feature_importances_
            model_desc = "GradientBoostingRegressor (sklearn fallback)"

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
        from sklearn.model_selection import TimeSeriesSplit

        n_splits = min(3, max(2, len(X) // 20))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]

            if use_lgb:
                cv_model = lgb.LGBMRegressor(
                    n_estimators=max(50, n_estimators // 2),
                    max_depth=max_depth,
                    learning_rate=lr,
                    num_leaves=num_leaves,
                    objective="regression",
                    random_state=ctx.seed,
                    verbosity=-1,
                )
            else:
                cv_model = GradientBoostingRegressor(
                    n_estimators=max(50, n_estimators // 2),
                    max_depth=max_depth,
                    learning_rate=lr,
                    loss="squared_error",
                    random_state=ctx.seed,
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
            if h + 1 < horizon:
                fc_features[h + 1] = _create_forecast_features(
                    np.array(extended_for_fc), 1, n_lags, rolling_windows
                )[0]

        fc_values = np.array(fc_values)

        progress_callback("Building output", 90)

        # Feature importance
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
            ["Algorithm", model_desc],
            ["Backend", backend],
            ["n_estimators", n_estimators],
            ["max_depth", max_depth],
            ["num_leaves", num_leaves],
            ["learning_rate", lr],
            ["subsample", subsample],
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
                "Consider reducing num_leaves or max_depth."
            )
        if horizon > n // 2:
            warn_list.append(
                f"Forecast horizon ({horizon}) is large relative to series length ({n}). "
                "Recursive multi-step forecasts degrade with longer horizons."
            )

        top_feature = feat_imp[0][0] if feat_imp else "N/A"
        plain_english = (
            f"LightGBM forecast for '{name}' ({n} observations) using {backend} with "
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

        return make_response(
            ctx,
            tables=[fc_table, summary_table, imp_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "backend": backend,
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "num_leaves": num_leaves,
                "learning_rate": lr,
                "subsample": subsample,
                "n_lags": n_lags,
                "n_features": len(feature_names),
                "train_rmse": round(train_rmse, 4),
                "train_mae": round(train_mae, 4),
                "train_r2": round(train_r2, 4),
                "cv_rmse": round(avg_cv_rmse, 4),
                "horizon": horizon,
                "top_feature": top_feature,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"LightGBM forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer lags or a simpler model (fewer leaves/estimators).",
                "Install lightgbm (pip install lightgbm) for native LightGBM support.",
                "Check that scikit-learn is installed for the fallback.",
            ],
        )
