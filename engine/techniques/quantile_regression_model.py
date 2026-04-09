"""
Quantile Regression Forecast for Time Series Lab.

Uses sklearn GradientBoostingRegressor with quantile loss to produce
forecasts at multiple quantile levels, providing full prediction intervals.
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
        "n_estimators": 100, "max_depth": 3, "learning_rate": 0.1,
        "n_lags": 6, "rolling_windows": [3],
        "quantiles": [0.1, 0.5, 0.9],
    },
    "Balanced": {
        "n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
        "n_lags": 12, "rolling_windows": [3, 6, 12],
        "quantiles": [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
    },
    "Thorough": {
        "n_estimators": 400, "max_depth": 5, "learning_rate": 0.02,
        "n_lags": 24, "rolling_windows": [3, 6, 12, 24],
        "quantiles": [0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975],
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
    """Create lag and rolling features. Returns X, y, feature_names."""
    n = len(series)
    features = []
    feature_names = []

    for lag in range(1, n_lags + 1):
        feat = np.full(n, np.nan)
        feat[lag:] = series[:-lag]
        features.append(feat)
        feature_names.append(f"lag_{lag}")

    for w in rolling_windows:
        feat = np.full(n, np.nan)
        for i in range(w, n):
            feat[i] = np.mean(series[i - w:i])
        features.append(feat)
        feature_names.append(f"roll_mean_{w}")

    for w in rolling_windows:
        if w >= 3:
            feat = np.full(n, np.nan)
            for i in range(w, n):
                feat[i] = np.std(series[i - w:i], ddof=1)
            features.append(feat)
            feature_names.append(f"roll_std_{w}")

    diff1 = np.full(n, np.nan)
    diff1[1:] = np.diff(series)
    features.append(diff1)
    feature_names.append("diff_1")

    time_idx = np.arange(n, dtype=float) / n
    features.append(time_idx)
    feature_names.append("time_index")

    X = np.column_stack(features)
    y = series.copy()

    valid_mask = ~np.any(np.isnan(X), axis=1)
    X = X[valid_mask]
    y = y[valid_mask]

    return X, y, feature_names


def _build_forecast_features(series, n_lags, rolling_windows):
    """Build feature vector for next-step prediction."""
    n = len(series)
    feat = []

    for lag in range(1, n_lags + 1):
        if n - lag >= 0:
            feat.append(series[n - lag])
        else:
            feat.append(0.0)

    for w in rolling_windows:
        if n >= w:
            feat.append(np.mean(series[n - w:n]))
        else:
            feat.append(np.mean(series))

    for w in rolling_windows:
        if w >= 3 and n >= w:
            feat.append(np.std(series[n - w:n], ddof=1))
        elif w >= 3:
            feat.append(0.0)

    if n >= 2:
        feat.append(series[-1] - series[-2])
    else:
        feat.append(0.0)

    feat.append(n / len(series))

    return np.array(feat)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Quantile regression forecast using gradient boosting.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    quantiles : list[float], optional
        Quantile levels to predict. Default from preset.
    n_lags : int, optional
        Number of lag features. Default from preset.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        from sklearn.ensemble import GradientBoostingRegressor

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
                "Quantile regression needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_lags = int(ctx.get_param("n_lags", preset_cfg["n_lags"]))
        n_estimators = int(ctx.get_param("n_estimators", preset_cfg["n_estimators"]))
        max_depth = int(ctx.get_param("max_depth", preset_cfg["max_depth"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["learning_rate"]))
        rolling_windows = preset_cfg["rolling_windows"]

        quantiles_param = ctx.get_param("quantiles", None)
        if quantiles_param is not None:
            if isinstance(quantiles_param, list):
                quantiles = sorted([float(q) for q in quantiles_param])
            else:
                quantiles = preset_cfg["quantiles"]
        else:
            quantiles = preset_cfg["quantiles"]

        # Ensure 0.5 is in quantiles (for median)
        if 0.5 not in quantiles:
            quantiles.append(0.5)
            quantiles.sort()

        n_lags = min(n_lags, n // 3)

        progress_callback("Creating features", 15)

        X, y, feature_names = _create_features(clean, n_lags, rolling_windows)
        if X is None or len(X) < 10:
            return make_error_response(
                ctx,
                "Not enough data points after feature creation.",
                error_fixes=["Reduce n_lags.", "Provide more data."],
            )

        progress_callback("Training quantile models", 25)

        # Train a model for each quantile
        models = {}
        n_quantiles = len(quantiles)
        for qi, q in enumerate(quantiles):
            pct = 25 + int(45 * qi / n_quantiles)
            progress_callback(f"Training quantile {q:.2f} model", pct)

            model = GradientBoostingRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=lr,
                loss="quantile",
                alpha=q,
                random_state=ctx.seed,
            )
            model.fit(X, y)
            models[q] = model

        progress_callback("Generating forecasts", 75)

        # Recursive multi-step forecast for each quantile
        quantile_forecasts = {q: [] for q in quantiles}

        for q in quantiles:
            extended = clean.tolist()
            for h in range(horizon):
                feat = _build_forecast_features(np.array(extended), n_lags, rolling_windows)
                pred = float(models[q].predict(feat.reshape(1, -1))[0])
                quantile_forecasts[q].append(pred)
                # Use median for recursive extension
                extended.append(pred)

        progress_callback("Building output", 90)

        # Forecast table
        fc_cols = ["Step"] + [f"Q{q:.3f}" for q in quantiles]
        fc_rows = []
        for i in range(horizon):
            row = [n + i + 1]
            for q in quantiles:
                row.append(round(float(quantile_forecasts[q][i]), 6))
            fc_rows.append(row)
        fc_table = make_table("Quantile Forecasts", fc_cols, fc_rows)

        # Prediction interval table (symmetric quantile pairs)
        interval_rows = []
        for i in range(horizon):
            row = [n + i + 1]
            median_val = quantile_forecasts[0.5][i]
            row.append(round(float(median_val), 6))
            # Find symmetric pairs
            lower_qs = [q for q in quantiles if q < 0.5]
            upper_qs = [q for q in quantiles if q > 0.5]
            for lq, uq in zip(lower_qs, reversed(list(upper_qs))):
                coverage = round((uq - lq) * 100, 0)
                lo = quantile_forecasts[lq][i]
                hi = quantile_forecasts[uq][i]
                row.extend([round(float(lo), 6), round(float(hi), 6)])

            interval_rows.append(row)

        interval_cols = ["Step", "Median"]
        lower_qs = [q for q in quantiles if q < 0.5]
        upper_qs = [q for q in quantiles if q > 0.5]
        for lq, uq in zip(lower_qs, reversed(list(upper_qs))):
            coverage = round((uq - lq) * 100, 0)
            interval_cols.extend([f"Lower {coverage:.0f}%", f"Upper {coverage:.0f}%"])
        interval_table = make_table("Prediction Intervals", interval_cols, interval_rows)

        # In-sample performance (median model)
        median_model = models[0.5]
        y_pred = median_model.predict(X)
        residuals = y - y_pred
        train_rmse = float(np.sqrt(np.mean(residuals ** 2)))
        train_mae = float(np.mean(np.abs(residuals)))

        # Check quantile crossing
        n_crossings = 0
        for i in range(horizon):
            vals = [quantile_forecasts[q][i] for q in quantiles]
            for j in range(len(vals) - 1):
                if vals[j] > vals[j + 1]:
                    n_crossings += 1

        if n_crossings > 0:
            warn_list.append(
                f"Quantile crossing detected at {n_crossings} point(s). "
                "Lower quantiles should not exceed upper quantiles. "
                "This can occur with independently trained quantile models."
            )

        summary_rows = [
            ["Algorithm", "Gradient Boosting (quantile loss)"],
            ["n_estimators", n_estimators],
            ["max_depth", max_depth],
            ["learning_rate", lr],
            ["n_lags", n_lags],
            ["Quantiles Modeled", len(quantiles)],
            ["Median Train RMSE", round(train_rmse, 4)],
            ["Median Train MAE", round(train_mae, 4)],
            ["Quantile Crossings", n_crossings],
            ["Horizon", horizon],
            ["Training Samples", len(X)],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        plain_english = (
            f"Quantile regression forecast for '{name}' ({n} observations) at "
            f"{len(quantiles)} quantile levels ({', '.join(f'{q:.2f}' for q in quantiles)}). "
            f"Median model train RMSE={train_rmse:.4f}. "
            f"{horizon}-step quantile forecasts produced."
        )
        if n_crossings > 0:
            plain_english += f" Warning: {n_crossings} quantile crossing(s) detected."

        charting = (
            "Fan chart: line chart of the median forecast with shaded prediction "
            "interval bands for each quantile pair (darker shading for narrower intervals). "
            "Overlay the original series."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[fc_table, interval_table, summary_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "n_quantiles": len(quantiles),
                "quantiles": [round(q, 3) for q in quantiles],
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "n_lags": n_lags,
                "train_rmse_median": round(train_rmse, 4),
                "n_crossings": n_crossings,
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Quantile regression forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer quantiles or lags.",
                "Check that scikit-learn is installed.",
            ],
        )
